import calendar
import datetime as dt

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

from config import (equipamentos_ativos, hist_handler, load_data, meses,
                    preventiva_historico, programacao)

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
def preventivas_realizadas(mes, ano):
    df = programacao(mes, ano)
    prev_hist = preventiva_historico()
    mes = meses()[mes.lower()]
    ano = int(ano)
    input_date = f'{ano}-{mes}-01'
    input_date = pd.to_datetime(input_date)

    if input_date in list(prev_hist['Data']):
        porcentagem_realizada = list(prev_hist.loc[prev_hist['Data'] == input_date]['Porcentagem Realizada'])[0]

        return porcentagem_realizada

    else:
        equip_realizado = len(df.loc[df['SITUAÇÃO'] == 'Realizado'])
        equip_nrealizado = len(df.loc[df['SITUAÇÃO'] == 'Não Realizado'])
        meta = equip_nrealizado + equip_realizado

        return (equip_realizado / meta)*100


@st.cache_data(ttl=600, show_spinner=False)
def equipamentos_realizados(mes, ano):
    df = programacao(mes, ano)
    prev_hist = preventiva_historico()
    mes = meses()[mes.lower()]
    ano = int(ano)
    input_date = f'{ano}-{mes}-01'
    input_date = pd.to_datetime(input_date)

    if input_date in list(prev_hist['Data']):
        equipamentos_realizados = list(prev_hist.loc[prev_hist['Data'] == input_date]['Numero Realizado'])[0]

        return equipamentos_realizados

    else:
        equip_realizado = len(df.loc[df['SITUAÇÃO'] == 'Realizado'])

        return equip_realizado


@st.cache_data(ttl=600, show_spinner=False)
def meta_mensal(mes, ano):
    df = programacao(mes, ano)
    prev_hist = preventiva_historico()
    mes = meses()[mes.lower()]
    ano = int(ano)
    input_date = f'{ano}-{mes}-01'
    input_date = pd.to_datetime(input_date)

    if input_date in list(prev_hist['Data']):
        porcentagem_realizada = list(prev_hist.loc[prev_hist['Data'] == input_date]['Porcentagem Realizada'])[0]
        equipamentos_realizados = int(list(prev_hist.loc[prev_hist['Data'] == input_date]['Numero Realizado'])[0])
        meta = round((equipamentos_realizados*100)/porcentagem_realizada)

        return meta

    else:
        equip_realizado = len(df.loc[df['SITUAÇÃO'] == 'Realizado'])
        equip_nrealizado = len(df.loc[df['SITUAÇÃO'] == 'Não Realizado'])
        meta = equip_nrealizado + equip_realizado

        return meta


@st.cache_data(ttl=600, show_spinner=False)
def preventiva_cliente(mes, ano):
    df = programacao(mes, ano)
    df = df[['CLIENTE', 'SITUAÇÃO']]
    df = df.loc[(df['SITUAÇÃO'] == "Realizado") | (df['SITUAÇÃO'] == "Não Realizado")]
    df_aux = df.groupby(by='CLIENTE', as_index=False).count()
    df_aux.rename(columns={'SITUAÇÃO': 'TOTAL'}, inplace=True)

    realizado = []
    n_realizado = []

    for row in df_aux.iterrows():
        cliente = row[1]['CLIENTE']

        no_realizado = len(df.loc[(df['CLIENTE'] == cliente) & (df['SITUAÇÃO'] == "Realizado")])
        no_nrealizado = len(df.loc[(df['CLIENTE'] == cliente) & (df['SITUAÇÃO'] == "Não Realizado")])

        realizado.append(no_realizado)
        n_realizado.append(no_nrealizado)

    df_aux['REALIZADO'] = realizado
    df_aux['NÃO REALIZADO'] = n_realizado

    df_aux['REALIZADO'] = df_aux.apply(lambda x: x['REALIZADO'] / x['TOTAL'], axis=1)
    df_aux = df_aux[['CLIENTE', 'REALIZADO']]

    return df_aux


@st.cache_data(ttl=600, show_spinner=False)
def preventiva_realizada_tecnico(mes, ano):
    df = hist_handler(load_data("HISTORICO_DATA!A:Y"))
    start_date = pd.to_datetime(
        f'{ano}-{meses()[str(mes).lower()]}-01')
    end_date = pd.to_datetime(
        f'{ano}-{meses()[str(mes).lower()]}-{calendar.monthrange(int(ano), meses()[str(mes).lower()])[1]} 23:59:00')
    bar_chart1_data = df.loc[(df['TIPO DE MANUTENÇÃO'] == 'INSPEÇÃO PREVENTIVA') &
                             (df['DATA TRABALHO'] >= start_date) &
                             (df['DATA TRABALHO'] <= end_date)]
    bar_chart1_data = bar_chart1_data.loc[(bar_chart1_data['STATUS ATENDIMENTO'] == 'Validado') |
                                          (bar_chart1_data['STATUS ATENDIMENTO'] == 'Concluido')]
    bar_chart1_data = bar_chart1_data[['Nº de Série', 'NOME TÉCNICO']]
    bar_chart1_data = bar_chart1_data.groupby('NOME TÉCNICO').count()
    bar_chart1_data = bar_chart1_data.rename(
        columns={'Nº de Série': 'PREVENTIVAS REALIZADAS'})
    bar_chart1_data = bar_chart1_data.sort_values(by='PREVENTIVAS REALIZADAS',
                                                  ascending=True)
    bar_chart1_data = bar_chart1_data.tail(10)

    fig = px.bar(bar_chart1_data,
                 x='PREVENTIVAS REALIZADAS',
                 orientation='h',
                 height=300,
                 )
    fig.update_traces(marker=dict(color='#F78604'))
    fig.update_xaxes(title_text='')
    fig.update_yaxes(title_text='')
    fig.update_traces(hovertemplate='%{x}')
    fig.update_layout(title={'text': 'Preventivas Realizadas x Técnico',
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

            side_c1, side_c2 = st.columns(2)
            today = dt.date.today()

            with side_c1:
                mes = st.selectbox(label="Selecione o Mês",
                                   options=[i.capitalize() for i in list(meses().keys())],
                                   index=today.month - 1)

            with side_c2:
                years = ["2022", "2023", "2024"]
                ano = str(dt.date.today().year)
                ano = st.selectbox(label="Selecione o Ano",
                                   options=years,
                                   index=years.index(ano))

            st.divider()

            if st.button('Recarregar', type='primary'):
                st.cache_data.clear()

            st.divider()

            authenticator.logout(button_name='Sair')

        indicadores, dados = st.tabs(["📈 Indicadores", "🗃 Dados"])

        with indicadores:

            r1c1, r1c2, r1c3, r1c4 = st.columns(4)

            with r1c1:
                r1c1_a, r1c1_b = st.columns(spec=[2, 8])
                with r1c1_a:
                    st.header('✅')
                with r1c1_b:
                    st.metric('Equipamentos Ativos', len(equipamentos_ativos()))

            with r1c2:
                r1c2_a, r1c2_b = st.columns(spec=[2, 8])
                with r1c2_a:
                    st.header('✔')
                with r1c2_b:
                    st.metric('Preventivas Realizadas', f'{preventivas_realizadas(mes, ano):.2f} %')

            with r1c3:
                r1c3_a, r1c3_b = st.columns(spec=[2, 8])
                with r1c3_a:
                    st.header('⚙')
                with r1c3_b:
                    st.metric('Equipamentos Realizados', equipamentos_realizados(mes, ano))

            with r1c4:
                r1c4_a, r1c4_b = st.columns(spec=[2, 8])
                with r1c4_a:
                    st.header('🚀')
                with r1c4_b:
                    st.metric('Meta Mensal', meta_mensal(mes, ano))

            r2c1, r2c2 = st.columns(2)
            prev_cliente = preventiva_cliente(mes, ano)

            with r2c1:
                st.data_editor(
                    prev_cliente,
                    column_config={
                        'REALIZADO': st.column_config.ProgressColumn(
                            "REALIZADO",
                        )
                    },
                    hide_index=True,
                    disabled=True,
                    use_container_width=True,
                    height=300
                )

            with r2c2:
                st.plotly_chart(preventiva_realizada_tecnico(mes, ano), use_container_width=True)

        with dados:
            st.data_editor(
                programacao(mes, ano),
                column_config={
                    'LINK': st.column_config.LinkColumn(
                        'Abrir OS',
                        display_text='Abrir OS',
                        width='small'
                    )
                },
                hide_index=True,
                disabled=True,
                use_container_width=True
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
