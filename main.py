import requests
import pandas as pd
from datetime import datetime
import dash
from dash import dcc, html, page_container
import plotly.express as px
import plotly.graph_objects as go


def get_jira_data():
    jira_url = 'https://issues.apache.org/jira/rest/api/2/search'
    query = {
        'jql': 'project = Kafka AND status = Closed',
        'fields': 'key,summary,created,resolutiondate,assignee,reporter,timespent,priority',
        'expand': 'changelog',
        'maxResults': 1000
    }
    response = requests.get(jira_url, params=query)
    return response.json()

DATA = get_jira_data()


def task1_layout():
    tasks = []
    for issue in DATA['issues']:
        created = datetime.strptime(issue['fields']['created'], '%Y-%m-%dT%H:%M:%S.%f%z')
        resolutiondate = datetime.strptime(issue['fields']['resolutiondate'], '%Y-%m-%dT%H:%M:%S.%f%z')
        open_time = (resolutiondate - created).total_seconds() / 3600  # В часах
        tasks.append(open_time)

    df = pd.DataFrame({'Open Time (hours)': tasks})
    fig = px.histogram(df, x='Open Time (hours)', nbins=20, title='Гистограмма времени в открытом состоянии')

    return html.Div([
        html.H1("Task 1: Time in Open State"),
        dcc.Graph(figure=fig),
    ])


def task2_layout():
    state_times = []

    for issue in DATA['issues']:
        changelog = issue.get('changelog', {}).get('histories', [])
        created = datetime.strptime(issue['fields']['created'], '%Y-%m-%dT%H:%M:%S.%f%z')

        transitions = []
        for change in changelog:
            for item in change['items']:
                if item['field'] == 'status':
                    transition_time = datetime.strptime(change['created'], '%Y-%m-%dT%H:%M:%S.%f%z')
                    transitions.append((item['fromString'], item['toString'], transition_time))

        transitions.sort(key=lambda x: x[2])
        for i, (from_status, to_status, transition_time) in enumerate(transitions):
            if i == 0:
                duration = (transition_time - created).total_seconds() / 3600  # Время в часах
                state_times.append({'State': from_status, 'Time in State (hours)': duration})

            if i > 0:
                prev_time = transitions[i - 1][2]
                duration = (transition_time - prev_time).total_seconds() / 3600
                state_times.append({'State': from_status, 'Time in State (hours)': duration})

        if transitions:
            last_status, _, last_time = transitions[-1]
            resolution_time = datetime.strptime(issue['fields']['resolutiondate'], '%Y-%m-%dT%H:%M:%S.%f%z')
            duration = (resolution_time - last_time).total_seconds() / 3600
            state_times.append({'State': last_status, 'Time in State (hours)': duration})

    df = pd.DataFrame(state_times)
    unique_states = df['State'].unique()


    graphs = []
    for state in unique_states:
        fig = px.histogram(
            df[df['State'] == state],
            x='Time in State (hours)',
            nbins=20,
            title=f'Время задач в состоянии: {state}'
        ).update_layout(
                xaxis_title='Время в состоянии (часы)',
                yaxis_title='Количество задач',
                template='plotly_white'
        )
        graphs.append(html.Div([
            html.H3(f"State: {state}"),
            dcc.Graph(figure=fig)
        ]))

    return html.Div([
        html.H1("Task 2: Time Distribution by State"),
        *graphs,
    ])

# Задание 3: График количества заведенных и закрытых задач
def task3_layout():
    issues = DATA['issues']
    
    # Создаем DataFrame
    rows = []
    for issue in issues:
        created_date = datetime.strptime(issue['fields']['created'], '%Y-%m-%dT%H:%M:%S.%f%z').date()
        resolution_date = datetime.strptime(issue['fields']['resolutiondate'], '%Y-%m-%dT%H:%M:%S.%f%z').date()
        rows.append({'Date': created_date, 'Type': 'Created'})
        rows.append({'Date': resolution_date, 'Type': 'Closed'})
    
    df = pd.DataFrame(rows)
    
    # Группируем данные по дате и типу
    daily_counts = df.groupby(['Date', 'Type']).size().reset_index(name='Count')
    
    # Создаем временной диапазон
    all_dates = pd.date_range(daily_counts['Date'].min(), daily_counts['Date'].max())
    
    # Заполняем пропущенные даты
    created_counts = daily_counts[daily_counts['Type'] == 'Created'].set_index('Date').reindex(all_dates, fill_value=0)['Count']
    closed_counts = daily_counts[daily_counts['Type'] == 'Closed'].set_index('Date').reindex(all_dates, fill_value=0)['Count']
    
    # Вычисляем накопительный итог
    cumulative_created = created_counts.cumsum()
    cumulative_closed = closed_counts.cumsum()
    
    # Построение графика
    fig = go.Figure()
    fig.add_trace(go.Bar(x=all_dates, y=created_counts, name="Created (Daily)", marker_color="blue"))
    fig.add_trace(go.Bar(x=all_dates, y=closed_counts, name="Closed (Daily)", marker_color="red"))
    fig.add_trace(go.Scatter(x=all_dates, y=cumulative_created, mode="lines", name="Created (Cumulative)", line=dict(color="blue", width=2)))
    fig.add_trace(go.Scatter(x=all_dates, y=cumulative_closed, mode="lines", name="Closed (Cumulative)", line=dict(color="red", width=2)))
    
    fig.update_layout(
        title="Количество заведенных и закрытых задач с накопительным итогом",
        xaxis_title="Дата",
        yaxis_title="Количество задач",
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return html.Div([
        html.H1("Task 3: Opened and Closed Issues Over Time"),
        dcc.Graph(figure=fig),
    ])


def task4_layout():
    issues = DATA['issues']

    user_data = []
    for issue in issues:
        assignee = issue['fields']['assignee']['displayName'] if issue['fields']['assignee'] else "Unassigned"
        reporter = issue['fields']['reporter']['displayName'] if issue['fields']['reporter'] else "Unknown Reporter"
        
        user_data.append({'User': assignee, 'Role': 'Assignee'})
        user_data.append({'User': reporter, 'Role': 'Reporter'})

    df = pd.DataFrame(user_data)

    user_counts = df.groupby(['User', 'Role']).size().reset_index(name='Count')

    total_counts = user_counts.groupby('User')['Count'].sum().sort_values(ascending=False).head(30).index
    top_users = user_counts[user_counts['User'].isin(total_counts)]
    
    # Построение горизонтальной гистограммы
    fig = px.bar(
        top_users,
        x='Count',
        y='User',
        color='Role',
        orientation='h',
        title='Количество задач для пользователей (исполнитель и репортер)',
        labels={'Count': 'Количество задач', 'User': 'Пользователь'}
    )
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    
    return html.Div([
        html.H1("Task 4: Task Distribution by Users"),
        dcc.Graph(figure=fig),
    ])


def task5_layout():
    issues = DATA['issues']

    task_data = []
    for issue in DATA['issues']:
        changelog = issue['changelog']['histories']
        closed_time = None
        started_time = None

        for change in changelog:
            for item in change['items']:
                if item['field'] == 'status':
                    if item['toString'] == 'Closed':
                        closed_time = change['created']
                    elif item['toString'] in ['In Progress', 'Open']:
                        started_time = change['created']

        if closed_time and started_time:
            closed_time = pd.to_datetime(closed_time)
            started_time = pd.to_datetime(started_time)
            duration = (closed_time - started_time).total_seconds() / 3600  # Часы
            task_data.append(duration)

    df = pd.DataFrame({'TimeSpentHours': task_data})

    bins = [0, 1, 2, 4, 8, 16, 32, 64, 128]
    labels = ['<1h', '1-2h', '2-4h', '4-8h', '8-16h', '16-32h', '32-64h', '64-128h']
    df['TimeCategory'] = pd.cut(df['TimeSpentHours'], bins=bins, labels=labels, right=False)

    grouped = df['TimeCategory'].value_counts().reset_index()
    grouped.columns = ['TimeCategory', 'TaskCount']
    grouped.sort_values('TimeCategory', inplace=True)

    fig = px.bar(
        grouped,
        x='TimeCategory',
        y='TaskCount',
        title='Время выполнения задач (часы)',
        labels={'TimeCategory': 'Категория времени', 'TaskCount': 'Количество задач'},
        text='TaskCount'
    )
    fig.update_traces(textposition='outside')

    return html.Div([
        html.H1("Task 5: Logged Time Histogram"),
        dcc.Graph(figure=fig),
    ])

def task6_layout():
    issues = DATA['issues']

    priorities = [issue['fields']['priority']['name'] if issue['fields']['priority'] else 'Undefined' for issue in issues]

    df = pd.DataFrame({'Priority': priorities})
    priority_counts = df['Priority'].value_counts().reset_index()
    priority_counts.columns = ['Priority', 'Count']

    priority_order = ['Critical', 'Blocker', 'Major', 'Minor', 'Trivial', 'Undefined']
    priority_counts['Priority'] = pd.Categorical(priority_counts['Priority'], categories=priority_order, ordered=True)
    priority_counts.sort_values('Priority', inplace=True)

    fig = px.bar(
        priority_counts,
        x='Priority',
        y='Count',
        title='Количество задач по степени серьезности',
        labels={'Priority': 'Степень серьезности', 'Count': 'Количество задач'},
        text='Count'
    )
    fig.update_traces(textposition='outside')

    return html.Div([
        html.H1("Task 6: Issues by Priority"),
        dcc.Graph(figure=fig),
    ])


app = dash.Dash(__name__, use_pages=True, pages_folder='')

app.layout = html.Div([
    html.H1("Dash Application for JIRA Analytics"),
    html.Nav([
        html.A("Task 1: Open Time Histogram", href="/task1", style={'margin-right': '20px'}),
        html.A("Task 2: Time by State", href="/task2", style={'margin-right': '20px'}),
        html.A("Task 3: Created and Closed Issues", href="/task3", style={'margin-right': '20px'}),
        html.A("Task 4: User Task Distribution", href="/task4", style={'margin-right': '20px'}),
        html.A("Task 5: Logged Time Histogram", href="/task5", style={'margin-right': '20px'}),
        html.A("Task 6: Issues by Priority", href="/task6", style={'margin-right': '20px'})
    ]),
    page_container
])


dash.register_page("task1", path="/task1", layout=task1_layout())
dash.register_page("task2", path="/task2", layout=task2_layout())
dash.register_page("task3", path="/task3", layout=task3_layout())
dash.register_page("task4", path="/task4", layout=task4_layout())
dash.register_page("task5", path="/task5", layout=task5_layout())
dash.register_page("task6", path="/task6", layout=task6_layout())


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)
