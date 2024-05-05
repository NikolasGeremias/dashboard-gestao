import calendar
import os
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SPREADSHEET_ID = '1zPlBWcCxCRqLOCe5tWfIPdfcuMB78KIoro4u4Y6hh5E'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
DISCOVERY_SERVICE_URL = 'https://sheets.googleapis.com/$discovery/rest?version=v4'
MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12
}


@st.cache_data(ttl=600, show_spinner=False)
def get_service(creds=None):
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file(
            'token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('sheets', 'v4', credentials=creds)
        return service

    except Exception:
        service = build('sheets', 'v4', credentials=creds,
                        discoveryServiceUrl=DISCOVERY_SERVICE_URL)

        return service


@st.cache_data(ttl=600, show_spinner=False)
def load_data(range_data, **kwargs):
    '''Returns a table in pandas dataframe type'''

    if 'max_attempts' in kwargs:
        max_attempts = kwargs['max_attempts']
    else:
        max_attempts = 3

    if 'tolerance' in kwargs and kwargs['tolerance'] >= 0.7:
        tolerance = kwargs['tolerance']
    else:
        tolerance = 0.7

    for attempt in range(max_attempts):
        try:
            # Get return from google sheets API
            service = get_service()
            result = service.spreadsheets().values().get(
                spreadsheetId=SPREADSHEET_ID, range=range_data).execute()

            # Organize data to turn into dataframe
            values = result['values']
            data = {}
            table_len = len(values[0])
            for j, column in enumerate(values[0]):
                column_list = []
                for i, row in enumerate(values):
                    if i == 0:
                        continue
                    if len(row) != table_len:
                        while len(row) != table_len + 1:
                            row.append("")

                    if not row.count("") > tolerance*table_len:
                        column_list.append(row[j])

                data[column] = column_list
                df = pd.DataFrame(data=data)

            return df
        except HttpError as error:
            print(f"Attempt {attempt}:{error}")

    print('Max attempts reached')
    return None


@st.cache_data(ttl=600, show_spinner=False)
def meses():
    return MONTHS


@st.cache_data(ttl=600, show_spinner=False)
def hist_handler(data):
    df_hist = data
    df_hist['DATA TRABALHO'] = pd.to_datetime(df_hist['DATA TRABALHO'],
                                              errors='coerce',
                                              dayfirst=True)
    df_hist['DATA ABERTURA OS'] = pd.to_datetime(df_hist['DATA ABERTURA OS'],
                                                 errors='coerce',
                                                 dayfirst=True)
    df_hist['DURAÇÃO IDA'] = pd.to_timedelta(df_hist['DURAÇÃO IDA'])
    df_hist['DURAÇÃO TRABALHO'] = pd.to_timedelta(
        df_hist['DURAÇÃO TRABALHO'])
    df_hist['DURAÇÃO VOLTA'] = pd.to_timedelta(df_hist['DURAÇÃO VOLTA'])

    return df_hist


@st.cache_data(ttl=600, show_spinner=False)
def equipamentos_ativos():
    df = load_data('Lista de Equipamentos!A:AY')
    df = df.loc[df['Status'] == 'ATIVO', 'Nº de Série']
    return list(df)


@st.cache_data(ttl=600, show_spinner=False)
def preventiva_historico():
    df = load_data('PREVENTIVAS_MENSAL_PLT!A:E')
    df['Data'] = pd.to_datetime(df['Data'],
                                errors='coerce',
                                dayfirst=True)
    df['Porcentagem Realizada'] = df['Porcentagem Realizada'].str.replace('%', '').str.replace(',', '.')
    df['Porcentagem em Conformidade'] = df['Porcentagem em Conformidade'].str.replace('%', '').str.replace(',', '.')

    df['Porcentagem Realizada'] = pd.to_numeric(df['Porcentagem Realizada'], errors='coerce')
    df['Porcentagem em Conformidade'] = pd.to_numeric(df['Porcentagem em Conformidade'], errors='coerce')

    return df


@st.cache_data(ttl=600, show_spinner=False)
def calcula_data(dias):
    data_atual = datetime.now()
    data_filtro = data_atual - timedelta(days=dias)
    data_filtro = data_filtro.replace(hour=0, minute=0, second=0, microsecond=0)

    return data_filtro


@st.cache_data(ttl=600, show_spinner=False)
def ultimo_g4_equip(sorted_column):
    '''
        Retorna um dataframe com os ultimos atendimentos de cada equipamento ativo
    '''
    ativos = equipamentos_ativos()
    historico_data = hist_handler(load_data('HISTORICO_DATA!A:Y'))

    columns = historico_data.columns.values
    historico_grouped = historico_data.set_index('Nº de Série')

    equipamentos = historico_grouped.index.values
    equipamentos = list(set(list(equipamentos)))

    result = pd.DataFrame(columns=columns)

    for equip in ativos:
        if equip in equipamentos:
            df_aux = historico_grouped.loc[[equip]]
            df_aux = df_aux.loc[df_aux['STATUS DO EQUIPAMENTO'] != ""]
            df_aux = df_aux.sort_values(by=sorted_column)
            df_aux = df_aux.tail(1)

            result = pd.concat([result, df_aux])
        else:
            continue

    return result


@st.cache_data(ttl=600, show_spinner=False)
def cronograma(mes, ano):

    def func(row, date_input):
        if date_input > row['data_aux']:
            if int(row['pmes_aux']) % 2 == 0:
                x = True if mes % int(row['pfreq_aux']) == 0 else False
            else:
                x = True if (mes + 1) % int(row['pfreq_aux']) == 0 else False
        else:
            x = False
        return x

    df_equip = load_data("Lista de Equipamentos!A:AY")
    df = df_equip.loc[df_equip['Status'] == 'ATIVO']

    df_os = load_data('OS Preventivas!C5:H')
    df_os['Data'] = pd.to_datetime(df_os['Data'],
                                   errors='coerce',
                                   dayfirst=True)

    input_date = f'{ano}-{mes}-01'
    input_date = datetime.strptime(input_date, '%Y-%m-%d').date()

    df['pmes_aux'] = df['Periodicidade'].apply(
        lambda x: x[-1:] if len(x) == 2 else x[-2:])
    df['pfreq_aux'] = df['Periodicidade'].apply(
        lambda x: 1 if x[0] == "A" else (2 if x[0] == "B" else 3))
    df['data_aux'] = df.apply(lambda x: date(
        int(x['Inicio periodicidade']), int(x['pmes_aux']), 1), axis=1)
    df['cronograma'] = df.apply(func, axis=1, args=(input_date,))

    df = df[['Nº de Série', 'Periodicidade', 'Classe', 'Inicio periodicidade',
             'LOCALIZAÇÃO', 'Máquina', 'Modelo', 'Cidade', 'cronograma']]
    df.rename(columns={'Nº de Série': 'Série'}, inplace=True)

    return df


@st.cache_data(ttl=600, show_spinner=False)
def programacao(mes, ano):

    def link_g4(row):
        try:
            return 'http://g4.transpotech.com.br/transpotech/os/detalhar/' + str(row[0][:row[0].index('-')])
        except IndexError:
            return ""

    def situacao(row):
        if row['cronograma']:
            if row['Realizado']:
                return 'Realizado'
            else:
                return 'Não Realizado'
        else:
            return 'Não Fazer'

    mes = MONTHS[mes.lower()]
    ano = int(ano)
    df = cronograma(mes, ano)
    df_hist = hist_handler(load_data("HISTORICO_DATA!A:Y"))

    df_horimetro = ultimo_g4_equip('DATA TRABALHO').reset_index()
    df_horimetro.rename(columns={'index': 'Série'}, inplace=True)
    df_horimetro = df_horimetro[['Série', 'HORÍMETRO']]

    input_date = f'{ano}-{mes}-01'
    input_date = datetime.strptime(input_date, '%Y-%m-%d').date()
    start_date = pd.to_datetime(f'{ano}-{mes}-01')
    end_date = pd.to_datetime(f'{ano}-{mes}-{calendar.monthrange(ano, mes)[1]} 23:59:00')

    os_mes = load_data('OS Preventivas!C5:H')
    os_mes['Data'] = pd.to_datetime(os_mes['Data'],
                                    errors='coerce',
                                    dayfirst=True)
    os_mes = os_mes.loc[os_mes['Data'] == start_date]
    os_mes = os_mes[['Série', 'Nº OS']]

    data = df.merge(os_mes, on='Série', how='left')

    df_hist = df_hist.loc[(df_hist['TIPO DE MANUTENÇÃO'] == 'INSPEÇÃO PREVENTIVA') &
                          (df_hist['DATA TRABALHO'] >= start_date) &
                          (df_hist['DATA TRABALHO'] <= end_date)]

    df1 = df_hist.loc[(df_hist['STATUS ATENDIMENTO'] == 'Validado') |
                      (df_hist['STATUS ATENDIMENTO'] == 'Concluido') |
                      (df_hist['STATUS ATENDIMENTO'] == 'Cancelado')]
    df1 = df1[['Nº de Série', 'STATUS ATENDIMENTO', 'CÓDIGO OS APOLLO']]
    df1.rename(columns={'STATUS ATENDIMENTO': 'atendimentos concluidos', 'Nº de Série': 'Série'}, inplace=True)

    df2 = df_hist[['Nº de Série', 'STATUS ATENDIMENTO', 'CÓDIGO OS APOLLO']]
    df2.rename(columns={'STATUS ATENDIMENTO': 'atendimentos total', 'Nº de Série': 'Série'}, inplace=True)

    realizados = []
    for row in data.iterrows():
        serie = row[1]['Série']
        os_row = row[1]['Nº OS']
        concluidos_df = df1.loc[df1['Série'] == serie]
        atendimentos_df = df2.loc[df2['Série'] == serie]
        concluidos = len(df1.loc[df1['Série'] == serie])
        atendimentos = len(df2.loc[df2['Série'] == serie])

        if atendimentos_df['CÓDIGO OS APOLLO'].nunique() > 1:
            concluidos = len(concluidos_df.loc[concluidos_df['CÓDIGO OS APOLLO'] == os_row])
            atendimentos = len(atendimentos_df.loc[atendimentos_df['CÓDIGO OS APOLLO'] == os_row])
            if atendimentos == concluidos:
                realizados.append(True)
            else:
                realizados.append(False)
        else:
            if atendimentos == 0:
                realizados.append(False)
            else:
                if atendimentos == concluidos:
                    realizados.append(True)
                else:
                    realizados.append(False)

    data['Realizado'] = realizados
    data = data.merge(df_horimetro, on='Série', how='left')

    os_g4 = []
    status = []
    for row in data.iterrows():
        os_row = row[1]['Nº OS']
        df_aux = df_hist.loc[df_hist['CÓDIGO OS APOLLO'] == os_row]
        df_aux = df_aux[['CÓDIGO OS APOLLO', 'CÓDIGO OS G4', 'STATUS ATENDIMENTO']]

        os_g4.append(list(df_aux['CÓDIGO OS G4']))
        status.append(list(df_aux['STATUS ATENDIMENTO']))

    data['OS G4'] = os_g4
    data['STATUS G4'] = status
    data['LINK'] = data['OS G4'].apply(link_g4)
    data['SITUAÇÃO'] = data.apply(situacao, axis=1)

    data.rename(columns={'Série': 'NÚMERO SÉRIE',
                         'Máquina': 'FROTA',
                         'Modelo': 'MODELO',
                         'LOCALIZAÇÃO': 'CLIENTE',
                         'Classe': 'CLASSE',
                         'Cidade': 'CIDADE',
                         'HORÍMETRO': 'HORÍMETRO ATUAL',
                         'Nº OS': 'OS APOLLO',
                         }, inplace=True)

    data = data[['NÚMERO SÉRIE', 'FROTA', 'MODELO', 'CLIENTE', 'CLASSE', 'CIDADE',
                 'HORÍMETRO ATUAL', 'LINK', 'OS APOLLO', 'SITUAÇÃO', 'OS G4', 'STATUS G4']]

    return data


@st.cache_data(ttl=600, show_spinner=False)
def ultima_atualizacao():
    log = load_data('LOG!A:A')
    data = log.tail(1).values[0][0]

    return data
