import pandas as pd
import plotly.express as px
import pydeck as pdk
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

from config import (calcula_data, hist_handler, load_data,
                    preventiva_historico, ultima_atualizacao)

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


@st.cache_data(ttl=600, show_spinner=False)
def mapa_cidades(cliente_filtro, classe_filtro):
    df_equip = load_data('Lista de Equipamentos!A:AY')
    df_equip = df_equip.loc[df_equip['Status'] == 'ATIVO']
    df_equip['LOCALIZAÇÃO'] = df_equip['LOCALIZAÇÃO'].str.strip()
    df_equip['Cidade'] = df_equip['Cidade'].str.strip()
    df_equip['Cidade'] = df_equip['Cidade'].str.lower()
    df_equip = df_equip[['Cidade', 'LOCALIZAÇÃO', 'Classe']]

    df_coord = load_data('Coordenadas!A:C')
    df_coord['Latitude'] = df_coord['Latitude'].str.replace(',', '.')
    df_coord['Longitude'] = df_coord['Longitude'].str.replace(',', '.')
    df_coord['Latitude'] = pd.to_numeric(df_coord['Latitude'], errors='coerce')
    df_coord['Longitude'] = pd.to_numeric(df_coord['Longitude'], errors='coerce')
    df_coord['COORDINATES'] = df_coord.apply(lambda x: [x['Longitude'], x['Latitude']], axis=1)
    df_coord = df_coord[['Cidade', 'COORDINATES']]

    df = df_equip.merge(df_coord, on='Cidade', how='left')
    df.rename(columns={'Cidade': 'ADDRESS', 'LOCALIZAÇÃO': 'SPACES'}, inplace=True)

    if cliente_filtro:
        df = df.loc[df['SPACES'].isin(cliente_filtro)]

    if classe_filtro:
        df = df.loc[df['Classe'].isin(classe_filtro)]

    layer = pdk.Layer(
        "GridLayer",
        data=df,
        pickable=True,
        extruded=True,
        cell_size=2000,
        auto_highlight=True,
        elevation_scale=200,
        elevation_range=[0, 100],
        get_position="COORDINATES",
        get_elevation='SPACES',
        opacity=0.15
    )

    view_state = pdk.ViewState(latitude=-26.2999781860954,
                               longitude=-48.8613371983959,
                               zoom=9,
                               bearing=0,
                               pitch=45,
                               height=400)

    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "Equipamentos Ativos: {elevationValue}"},
    )

    return r


@st.cache_data(ttl=600, show_spinner=False)
def filtro_cliente():
    df = load_data('Lista de Equipamentos!A:AY')
    df['LOCALIZAÇÃO'] = df['LOCALIZAÇÃO'].str.strip()
    df = df.loc[df['Status'] == 'ATIVO', 'LOCALIZAÇÃO']

    equipamentos = list(set(list(df)))
    equipamentos = sorted(equipamentos)

    return equipamentos


@st.cache_data(ttl=600, show_spinner=False)
def filtro_classe():
    df = load_data('Lista de Equipamentos!A:AY')
    df['Classe'] = df['Classe'].str.strip()
    df = df.loc[df['Status'] == 'ATIVO', 'Classe']

    equipamentos = list(set(list(df)))
    equipamentos = sorted(equipamentos)

    return equipamentos


@st.cache_data(ttl=600, show_spinner=False)
def preventiva_anual():
    line_chart1_data = preventiva_historico()
    colors = ['#2986cc', '#FF4B4B']
    fig = px.line(line_chart1_data,
                  x='Data',
                  y=["Porcentagem Realizada", "Porcentagem em Conformidade"],
                  markers=True,
                  height=350,
                  color_discrete_sequence=colors)
    fig.update_yaxes(tickformat=",.2%")
    fig.update_yaxes(showgrid=False)
    fig.update_layout(yaxis_title="",
                      legend_title="",
                      legend=dict(yanchor="top",
                                  y=1.5, xanchor="left",
                                  x=0.5),
                      margin=dict(r=10,
                                  l=20,
                                  t=10),
                      title={'text': 'Preventiva Anual',
                             'x': 0.05,
                             'font': {'family': 'Sans-serif',
                                      'size': 18,
                                      },
                             },
                      yaxis=dict(visible=False))

    return fig


@st.cache_data(ttl=600, show_spinner=False)
def ranking_clientes(dias):
    df_hist = hist_handler(load_data("HISTORICO_DATA!A:Y"))
    df_hist = df_hist.loc[df_hist['TIPO DE MANUTENÇÃO'] == 'CORRETIVA', ['Nº de Série', 'DATA TRABALHO']]
    data_filtro = calcula_data(dias)
    df_hist = df_hist.loc[df_hist['DATA TRABALHO'] >= data_filtro]

    df_equip = load_data('Lista de Equipamentos!A:AY')
    df_equip['LOCALIZAÇÃO'] = df_equip['LOCALIZAÇÃO'].str.strip()
    df_equip = df_equip[['Nº de Série', 'LOCALIZAÇÃO']]

    df = df_hist.merge(df_equip, on='Nº de Série', how='left')
    df = df.dropna(subset=['LOCALIZAÇÃO'])

    df = df.groupby(by='LOCALIZAÇÃO', as_index=False).count()
    df = df.sort_values(by='Nº de Série')
    df = df.tail(10)

    fig = px.bar(df,
                 x='Nº de Série',
                 y='LOCALIZAÇÃO',
                 orientation='h',
                 height=350,
                 )
    fig.update_traces(marker=dict(color='#F78604'))
    fig.update_xaxes(title_text='')
    fig.update_yaxes(title_text='')
    fig.update_traces(hovertemplate='%{x}')
    fig.update_layout(title={'text': 'Ranking Corretivas',
                             'x': 0.2,
                             'font': {'family': 'Sans-serif',
                                      'size': 18,
                                      },
                             })

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

        r1c1, r1c2 = st.columns([2, 5])

        with r1c1:
            st.subheader('Equipamentos Ativos')
            cliente_filtro = st.multiselect('Clientes', filtro_cliente(), placeholder='Selecione os Clientes')
            classe_filtro = st.multiselect('Classe', filtro_classe(),
                                           placeholder='Selecione as Classes',
                                           help='''
                                                    I: Contrabalançada Elétrica\n
                                                    II: Empilhadeira para armanezagem vertical (Ex: Retrátil)\n
                                                    III: Empilhadeira e transpaleteira com operador a pé\n
                                                    IV: Contrabalançada combustão com pneu cushion\n
                                                    V: Contrabalançada combustão com rodagem normal\n
                                                    VI: Rebocadores\n
                                                    AA: Plataformas''')

        with r1c2:
            st.pydeck_chart(mapa_cidades(cliente_filtro, classe_filtro))

        a, b = st.columns([12, 3])

        with b:
            dias = st.radio(label="Dias", options=[30, 60, 90], horizontal=True)

        r2c1, r2c2 = st.columns(2)

        with r2c1:
            st.plotly_chart(preventiva_anual(), use_container_width=True)

        with r2c2:
            st.plotly_chart(ranking_clientes(dias), use_container_width=True)

        st.toast(f'Bem vindo {st.session_state["name"]}')
        st.toast(f'''Última Atualização:\n{ultima_atualizacao()}''', icon='📋')

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
