import plotly.graph_objects as go
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from plotly.subplots import make_subplots
from yaml.loader import SafeLoader

from config import calcula_data, hist_handler, load_data, ultimo_g4_equip

st.set_page_config(page_title="Gestão de Frotas",
                   page_icon="🛠",
                   layout='wide')


with open('./config.yaml') as file:
    configuration = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    configuration['credentials'],
    configuration['cookie']['name'],
    configuration['cookie']['key'],
    configuration['cookie']['expiry_days'],
    configuration['pre-authorized']
)


def link_g4(row):
    return 'http://g4.transpotech.com.br/transpotech/os/detalhar/' + str(row['CÓDIGO OS G4'][:row['CÓDIGO OS G4'].index('-')])


@st.cache_data(ttl=600, show_spinner=False)
def ultimos_atendimentos(filtro):
    historico_data = hist_handler(load_data('HISTORICO_DATA!A:Y'))
    data_filtro = calcula_data(filtro)

    historico_data = historico_data.loc[historico_data['DATA ABERTURA OS'] >= data_filtro].sort_values(by='DATA ABERTURA OS', ascending=False)
    historico_data['Link G4'] = historico_data.apply(link_g4, axis=1)

    historico_data['DATA ABERTURA OS'] = historico_data['DATA ABERTURA OS'].dt.strftime('%d/%m/%Y %H:%M')

    historico_data = historico_data[['FROTA', 'Nº de Série', 'RAZÃO SOCIAL', 'DATA ABERTURA OS',
                                    'Link G4', 'CÓDIGO OS APOLLO', 'STATUS ATENDIMENTO', 'STATUS DO EQUIPAMENTO']]

    return historico_data


@st.cache_data(ttl=600, show_spinner=False)
def vias_parar(filtro):
    result = ultimo_g4_equip('DATA TRABALHO')
    data_filtro = calcula_data(filtro)

    result['Link G4'] = result.apply(link_g4, axis=1)

    result = result.loc[result['STATUS DO EQUIPAMENTO'] == 'Equipamento em vias de parar']
    result = result[['FROTA', 'RAZÃO SOCIAL', 'DATA TRABALHO', 'Link G4']]
    result = result.loc[result['DATA TRABALHO'] >= data_filtro]
    result = result.sort_values(by='DATA TRABALHO', ascending=True)
    result['DATA TRABALHO'] = result['DATA TRABALHO'].dt.strftime('%d/%m/%Y %H:%M')

    return result


@st.cache_data(ttl=600, show_spinner=False)
def parados(filtro):
    result = ultimo_g4_equip('DATA TRABALHO')
    data_filtro = calcula_data(filtro)

    result['Link G4'] = result.apply(link_g4, axis=1)

    result = result.loc[(result['STATUS DO EQUIPAMENTO'] == 'Equipamento parado') | (result['STATUS DO EQUIPAMENTO'] == 'Equipamento parado com risco de acidente')]
    result = result[['FROTA', 'RAZÃO SOCIAL', 'DATA TRABALHO', 'Link G4', 'STATUS DO EQUIPAMENTO']]
    result = result.loc[result['DATA TRABALHO'] >= data_filtro]
    result = result.sort_values(by='DATA TRABALHO', ascending=True)
    result['DATA TRABALHO'] = result['DATA TRABALHO'].dt.strftime('%d/%m/%Y %H:%M')

    return result


@st.cache_data(ttl=600, show_spinner=False)
def pendencias(filtro):
    result = ultimo_g4_equip('DATA TRABALHO')
    data_filtro = calcula_data(filtro)

    result['Link G4'] = result.apply(link_g4, axis=1)

    result = result.loc[result['PENDÊNCIA'] == 'Sim']
    result = result[['FROTA', 'RAZÃO SOCIAL', 'DATA TRABALHO', 'Link G4', 'COMENTÁRIO DO TÉCNICO', 'STATUS DO EQUIPAMENTO']]
    result = result.loc[result['DATA TRABALHO'] >= data_filtro]
    result = result.sort_values(by='DATA TRABALHO', ascending=True)
    result['DATA TRABALHO'] = result['DATA TRABALHO'].dt.strftime('%d/%m/%Y %H:%M')

    return result


@st.cache_data(ttl=600, show_spinner=False)
def metrics(status):
    df = ultimo_g4_equip('DATA TRABALHO')
    df = df.loc[df['STATUS DO EQUIPAMENTO'] == status]

    return len(df)


@st.cache_data(ttl=600, show_spinner=False)
def bar_pizza_subplot():
    df = ultimo_g4_equip('DATA TRABALHO')

    ativos = load_data('Lista de Equipamentos!A:AY')
    ativos = ativos.loc[ativos['Status'] == 'ATIVO']
    ativos = ativos[['Nº de Série', 'LOCALIZAÇÃO']]
    ativos = ativos.rename(columns={'Nº de Série': 'SÉRIE'})

    df_bar = df.reset_index(names='SÉRIE')
    df_bar = df_bar.drop('Nº de Série', axis=1)

    df_bar = df_bar.merge(ativos, on='SÉRIE')

    x = list(set(list(df_bar['LOCALIZAÇÃO'])))

    operando_lista = []
    parado_lista = []

    for cliente in x:
        df_aux = df_bar.loc[df_bar['LOCALIZAÇÃO'] == cliente]
        operando = len(df_aux.loc[(df_bar['STATUS DO EQUIPAMENTO'] == 'Equipamento operando') |
                                  (df_bar['STATUS DO EQUIPAMENTO'] == 'Equipamento em vias de parar')])
        parado = len(df_aux.loc[(df_bar['STATUS DO EQUIPAMENTO'] == 'Equipamento parado') |
                                (df_bar['STATUS DO EQUIPAMENTO'] == 'Equipamento parado com risco de acidente')])
        operando_lista.append(operando)
        parado_lista.append(parado)

    operando = len(df.loc[df['STATUS DO EQUIPAMENTO'] == 'Equipamento operando'])
    vias_de_parar = len(df.loc[df['STATUS DO EQUIPAMENTO'] == 'Equipamento em vias de parar'])
    parado = len(df.loc[df['STATUS DO EQUIPAMENTO'] == 'Equipamento parado'])
    parado_risco = len(df.loc[df['STATUS DO EQUIPAMENTO'] == 'Equipamento parado com risco de acidente'])

    labels = ['Equipamento operando', 'Equipamento em vias de parar', 'Equipamento parado', 'Equipamento parado com risco de acidente']
    values = [operando, vias_de_parar, parado, parado_risco]

    fig_pie = go.Figure(data=[go.Pie(labels=labels[::-1], values=values[::-1])])

    fig_bar = go.Figure(data=[
        go.Bar(name="Operando", x=x, y=operando_lista),
        go.Bar(name="Parado", x=x, y=parado_lista)
    ])

    fig = make_subplots(rows=1, cols=2, specs=[[{'type': 'domain'}, {'type': 'bar'}]])

    for trace in fig_pie.data:
        fig.add_trace(trace, row=1, col=1)

    for trace in fig_bar.data:
        fig.add_trace(trace, row=1, col=2)

    fig.update_layout(
        margin=dict(
            t=30,
            l=30,
            r=30
        ),
        legend=dict(
            orientation="v",
            x=0,
            y=-0.7
        ),
    )

    return fig


with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

authenticator.login(fields={'Form name': 'Dashboard Joinville',
                            'Username': 'Usuário',
                            'Password': 'Senha'})

if st.session_state['authentication_status']:
    try:
        with st.sidebar:
            st.image('img/logo_new.png', use_column_width='auto')
            st.page_link('Home.py', label='Home', icon='🏠')
            st.page_link('pages/Corretiva.py', label='Corretiva', icon='🔩')
            st.page_link('pages/Preventiva.py', label='Preventiva', icon='📆')

            st.divider()

            if st.button('Recarregar', type='primary'):
                st.cache_data.clear()

            st.divider()

            authenticator.logout(button_name='Sair')

        indicadores, dados = st.tabs(["📈 Indicadores", "🗃 Dados"])

        with indicadores:
            r1, r2, r3, r4 = st.columns(4)

            with r1:
                r1a1, r1a2 = st.columns(spec=[2, 8])
                with r1a1:
                    st.header('✅')
                with r1a2:
                    st.metric('Equipamentos Operando', metrics('Equipamento operando'))
            with r2:
                r1b1, r1b2 = st.columns(spec=[2, 8])
                with r1b1:
                    st.header('⚠️')
                with r1b2:
                    st.metric('Equipamentos em vias de parar', metrics('Equipamento em vias de parar'))
            with r3:
                r1c1, r1c2 = st.columns(spec=[2, 8])
                with r1c1:
                    st.header('🚨')
                with r1c2:
                    st.metric('Equipamentos parados ', metrics('Equipamento parado'))
            with r4:
                r1d1, r1d2 = st.columns(spec=[2, 8])
                with r1d1:
                    st.header('☠️')
                with r1d2:
                    st.metric('Equipamentos parados com risco de acidente ', metrics('Equipamento parado com risco de acidente'))
            st.subheader('Disponibilidade')

            st.plotly_chart(bar_pizza_subplot(), use_container_width=True, theme='streamlit')

        with dados:
            a1, a2 = st.columns([5, 1.5])
            with a1:
                st.subheader("Ultimos Atendimentos")
            with a2:
                dias = st.radio(label="Dias",
                                options=[1, 7, 30, 90],
                                horizontal=True)
            df_ultimos_atendimentos = ultimos_atendimentos(int(dias))
            st.data_editor(
                df_ultimos_atendimentos,
                column_config={
                    'Link G4': st.column_config.LinkColumn(
                        "Abrir OS",
                        display_text='Abrir OS'
                    )
                },
                hide_index=True,
                height=300,
                disabled=True,
                use_container_width=True,
            )

            pendencia_df = pendencias(dias)
            st.subheader("Pendências")
            st.data_editor(
                    pendencia_df,
                    column_config={
                        'Link G4': st.column_config.LinkColumn(
                            'Abrir OS',
                            display_text='Abrir OS'
                        )
                    },
                    hide_index=True,
                    height=300,
                    disabled=True,
                    use_container_width=True,
                )

            b1, b2 = st.columns(2)
            with b1:
                df_vias_parar = vias_parar(int(dias))
                st.subheader("Equipamentos em vias de parar")
                st.data_editor(
                    df_vias_parar,
                    column_config={
                        'Link G4': st.column_config.LinkColumn(
                            'Abrir OS',
                            display_text='Abrir OS'
                        )
                    },
                    hide_index=True,
                    height=300,
                    disabled=True,
                    use_container_width=True,
                )
            with b2:
                df_parados = parados(int(dias))
                st.subheader("Equipamentos Parados")
                st.data_editor(
                    df_parados,
                    column_config={
                        'Link G4': st.column_config.LinkColumn(
                            'Abrir OS',
                            display_text='Abrir OS'
                        )
                    },
                    hide_index=True,
                    height=300,
                    disabled=True,
                    use_container_width=True,
                )
    except TimeoutError:
        st.toast('Carregando. Por favor aguarde')
        st.cache_data.clear()

    except Exception as e:
        st.write('Favor contate o administrador')
        print(e)

elif st.session_state["authentication_status"] is False:
    st.error('Usuário/Senha incorreto')
elif st.session_state["authentication_status"] is None:
    st.warning('Insira seu usuário e senha')
