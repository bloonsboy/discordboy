import pandas as pd
from datetime import timedelta
import tabulate as tb
import matplotlib.pyplot as plt
import seaborn as sns
import re

MESSAGE_TYPES = ["DM", "GROUP_DM", "GUILD_TEXT", "PUBLIC_THREAD"]

def format_number(number):
    '''
    Put spaces between numbers
    '''
    return f"{number:,}".replace(",", " ")


def remove_spaces(text):
    '''
    Remove multiples spaces from the given text.
    '''
    text_clean = re.sub(r'\s+', ' ', text).strip()
    return text_clean


def ask_for_the_type():   
    '''
    Ask the user for the type of data he wants to analyse
    ''' 
    choice = input("Enter the type you want to analyse : DM, GROUP_DM, GUILD_TEXT, GUILD_VOICE or PUBLIC_THREAD").strip()
    choice = choice.upper()
    while choice not in ["DM", "GROUP_DM", "GUILD_TEXT", "GUILD_VOICE", "PUBLIC_THREAD"]:
        print("Invalid type")
        choice = input("Enter the type you want to analyse : DM, GROUP_DM, GUILD_TEXT, GUILD_VOICE or PUBLIC_THREAD").strip()
    return choice


def df_date(df):   
    '''
    Ask the user for the date range they want to analyse    
    ''' 
    date_input = input("Enter date limit in format YYYY-MM-DD or number of days (for interval, separate with a comma): ").strip()
    dates = date_input.split(',')
    
    if len(dates) == 1:
        date = dates[0].strip()
        while not date.replace("-", "").isdigit():
            print("Invalid date")
            date = input("Date limit in format YYYY-MM-DD or number of days").strip()
        if len(date) == 10:
            cutoff_date = pd.to_datetime(date)
            return df[pd.to_datetime(df['Timestamp']) >= cutoff_date]
        else:
            cutoff_date = pd.to_datetime(df['Timestamp']).max() - timedelta(days=int(date))
            return df[pd.to_datetime(df['Timestamp']) >= cutoff_date]
    elif len(dates) == 2:
        start_date, end_date = dates[0].strip(), dates[1].strip()
        while not (start_date.replace("-", "").isdigit() and end_date.replace("-", "").isdigit()):
            print("Invalid date range")
            date_input = input("Enter date limit in format YYYY-MM-DD or number of days (for interval, separate with a comma): ").strip()
            start_date, end_date = date_input.split(',')
            start_date, end_date = start_date.strip(), end_date.strip()
        if len(start_date) == 10 and len(end_date) == 10:
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)
        else:
            start_date = pd.to_datetime(df['Timestamp']).max() - timedelta(days=int(start_date))
            end_date = pd.to_datetime(df['Timestamp']).max() - timedelta(days=int(end_date))
        return df[(pd.to_datetime(df['Timestamp']) >= start_date) & (pd.to_datetime(df['Timestamp']) <= end_date)]
    else:
        print("Invalid input format")
        return df


def top_10_messages(df):
    '''
    Return the top 10 messages in the DataFrame.
    '''
    top_10_messages_data = [[i+1] for i in range(10)]
    total_count = []
    for message_type in MESSAGE_TYPES:
        if df[df["Type"] == message_type].empty:
            continue
        top_10_names = df[df["Type"] == message_type]["Name"].value_counts().head(10)
        for i, (name, count) in enumerate(top_10_names.items()):
            top_10_messages_data[i].append(f"{remove_spaces(name)} - {format_number(count)}")
        total_count.append(format_number(df[df["Type"] == message_type].shape[0]))
    top_10_messages_data.append([]*10)
    top_10_messages_data.append(["Total"] + total_count)
    create_table(top_10_messages_data, headers=["TOP 10"]+MESSAGE_TYPES)


def message_statistics(df):
    '''
    Return the number of messages by type in the DataFrame, along with percentages and median sizes.
    '''
    message_data = []
    for message_type in MESSAGE_TYPES:
        if df[df["Type"] == message_type].empty:
            continue
        df_type = df[df["Type"] == message_type]
        percentage = (len(df_type) / len(df)) * 100
        median_size = df_type["Contents"].str.len().median()

        message_data.append([
            message_type,
            format_number(len(df_type)),
            f"{percentage:.2f} %",
            f"{median_size} characters"
        ])
    create_table(message_data, headers=["Type", "Count", "Percentage", "Median Size"])


def plot_message_statistics(df, window=50, type="message"):
    '''
    Plot the number of messages by type over time in the DataFrame.
    '''
    plt.figure(figsize=(14, 10))
    for message_type in MESSAGE_TYPES:
        if df[df["Type"] == message_type].empty:
            continue
        df_type = df[df['Type'] == message_type].copy()
        df_type['Timestamp'] = pd.to_datetime(df_type['Timestamp']).dt.date
        if type == "character":
            df_type['len'] = df_type["Contents"].apply(lambda x: len(x) if isinstance(x, str) else 1)
            count = df_type.groupby('Timestamp')['len'].sum()
        else:
            count = df_type.groupby('Timestamp').size()
        smoothed_data = count.rolling(window=window, min_periods=1).mean()
        sns.lineplot(x=smoothed_data.index, y=smoothed_data.values, label=message_type)

    plt.xlabel('Date')
    plt.ylabel(f'Number of {type}s')
    plt.legend()
    plt.grid(True)
    plt.show()


def taille_message(df):
    '''
    Return the average size of messages in the DataFrame.
    '''
    df["Size"] = df["Contents"].str.len()
    sns.set_style("whitegrid")
    plt.figure(figsize=(16, 6))

    colors = ["blue", "green", "red", "purple", "orange"]
    for message_type, color in zip(["DM", "GROUP_DM", "GUILD_TEXT", "GUILD_VOICE", "PUBLIC_THREAD"], colors):
        message_sizes = df[df["Type"] == message_type]["Size"]
        bins = range(0, int(message_sizes.max()) + 5, 5)
        message_counts = pd.cut(message_sizes, bins=bins).value_counts().sort_index()
        message_percentages = (message_counts / len(message_sizes)) * 100
        sns.lineplot(x=message_percentages.index.categories.mid, y=message_percentages, label=message_type, color=color, alpha=0.6)
    plt.title('Percentage of message lengths by Type')
    plt.xlim(0, 50)
    plt.xlabel('Message Length (characters)')
    plt.ylabel('Percentage of messages')
    plt.legend(title='Message Type')
    plt.show()

    for message_type in ["DM", "GROUP_DM", "GUILD_TEXT", "GUILD_VOICE", "PUBLIC_THREAD"]:
        df_type = df[df["Type"] == message_type].copy()
        median_size = df_type["Size"].median()
        print(f"Size of messages in {message_type} : {median_size:.2f} characters\n")

#Print a table from table_data
def create_table(table_data, headers):
    tb.PRESERVE_WHITESPACE = False
    tb.WIDE_CHARS_MODE = True
    print(tb.tabulate(table_data, headers=headers, tablefmt="rst"))

