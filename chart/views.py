
from django.shortcuts import render
from datetime import datetime
import pandas as pd
import arrow
import json


def home(request):
    # return HttpResponse('코로나19 시각화 (준비 중)')
    dump = covid_dump()
    return render(request, 'chart/covid19.html', {'chart': dump,}, )


def load_data():
    # Section 2 - 데이터 적재 및 특정 국가 데이터 선별
    df = pd.read_csv(
        'https://raw.githubusercontent.com/datasets/covid-19/master/data/countries-aggregated.csv',
        parse_dates=['Date'])
    return df


def select_countries(df):
    # 분석 대상 국가에 해당하는 행만 선별
    countries = ['Korea, South', 'Germany', 'United Kingdom', 'US', 'France']  # 분석 대상 국가 리스트
    df = df[df['Country'].isin(countries)]
    return df, countries


def sum_cases(df):
    # Section 3 - 합계 열 계산
    # df['Cases'] = df[['Confirmed', 'Recovered', 'Deaths']].sum(axis=1)  # (확진자, 회복자, 사망자) 합계
    # df['Cases'] = df[['Deaths']].sum(axis='columns')   # 사망자 수치만 합계에 포함
    df['Cases'] = df[['Confirmed']].sum(axis='columns')  # 확진자 수치만 합계에 포함
    return df


def reshape(df):
    # Section 4 - 데이터 구조 재편
    covid = df.pivot(index='Date', columns='Country', values='Cases')
    # 필요한 특정 열만 columns로 지정하면, 해결됨
    covid.columns = covid.columns.to_list()  # 분석 대상 국가 리스트
    return covid


def read_population(countries):
    # 인구 데이터 읽어오기
    pop = pd.read_csv(
        'https://datahub.io/JohnSnowLabs/population-figures-by-country/r/population-figures-by-country-csv.csv')
    # 분석 대상 국가에서 국가 이름과 2016년도 인구 데이터만 추출
    pop = pop[
        pop['Country'].isin(countries)  # 코로나 데이터와 인구 데이터에서 국가명이 동일한 경우
        |  # 또는
        pop['Country'].isin(['United States', 'Korea, Rep.'])  # 코로나 데이터와 인구 데이터에서 국가명이 상이한 경우
        ][['Country', 'Year_2016']]  # 국가 이름 열과 2016년도 인구 데이터 열만 추출
    # 인구 데이터의 국가 이름을 코로나 데이터 기준으로 변경
    pop = pop.replace({'United States': 'US', 'Korea, Rep.': 'Korea, South'})
    # Country 열을 인덱스로 설정
    pop.set_index(['Country'], inplace=True)
    # 사전으로 변환
    pop = pop.to_dict()
    # 필요한 인구 데이터만 사전으로 추출
    populations = pop['Year_2016']
    return populations


def per_capita(covid, populations):
    # Section 5 - 백만명당 비율 계산
    percapita = covid.copy()
    for country in list(percapita.columns):
        percapita[country] = (percapita[country] / populations[country] * 1000000).round(2)
    return percapita


def make_my_data(percapita):
    my_data = list()
    for country in list(percapita.columns):
        my_series = list()
        for d in percapita.index.tolist():
            my_series.append(
                [arrow.get(d.year, d.month, d.day).timestamp * 1000, round(percapita.loc[d][country], 1)])
        my_dict = dict()
        my_dict['country'] = country
        my_dict['series'] = my_series
        my_data.append(my_dict)
    # for my_d in my_data:
    #     print(my_d['country'], my_d['series'], '\n')
    print(list(map(
        lambda entry: {'name': entry['country'], 'data': entry['series']},
        my_data)))
    return my_data


def make_chart(my_data):
    # Section 6 - highchart
    chart = {
        'chart': {
            'type': 'spline',
            'borderColor': '#9DB0AC',
            'borderWidth': 3,
        },
        'title': {'text': '인구 대비 COVID-19 확진자 비율'},
        'subtitle': {'text': 'Source: Johns Hopkins University Center for Systems Science and Engineering'},
        'xAxis': {'type': 'datetime',
                  # 'dateTimeLabelFormats': {'month': '%b \'%y'}
        },
        'yAxis': [{  # Primary yAxis
            'labels': {
                'format': '{value} 건/백만 명',
                'style': {'color': 'blue'}
            }, 'title': {
                'text': '누적 비율',
                'style': {'color': 'blue'}
            },
        }, ],
        'plotOptions': {
            'spline': {
                'lineWidth': 3,
                'states': {
                    'hover': {'lineWidth': 5}
                },
                # 'marker': {
                #     'enabled': 'false'
                # },
                # 'dataLabels': {
                #     'enabled': 'False'
                # },
            }
        },
        'series': list(map(
                    lambda entry: {'name': entry['country'], 'data': entry['series']},
                    my_data)
        ),
        'navigation': {
            'menuItemStyle': {'fontSize': '10px'}
        },
    }
    return chart


def my_converter(o):
    if isinstance(o, datetime):
        return o.__str__()


def covid_dump():
    df = load_data()
    df, countries = select_countries(df)
    df = sum_cases(df)
    covid = reshape(df)
    populations = read_population(countries)
    percapita = per_capita(covid, populations)
    date_line = percapita.index.tolist()
    my_data = make_my_data(percapita)
    chart = make_chart(my_data)
    dump = json.dumps(chart, default=my_converter)
    return dump