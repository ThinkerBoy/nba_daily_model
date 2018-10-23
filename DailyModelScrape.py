def dms_setup():
    import urllib.request
    from urllib.request import urlopen
    from bs4 import BeautifulSoup
    import pandas as pd
    import datetime
    import arrow
    import requests
    import bs4
    from shutil import copy2
    import os
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 1000)
    # today = time.strftime("%m/%d/%Y")

    # In[2]:

    database = "C:/Users/kmedvedovsky/Downloads/box/Personal/Python/Projects/NBA/Sheet/Databases"
    base = "C:/Users/kmedvedovsky/Downloads/box/Personal/Python/Projects/NBA/Sheet"
    os.chdir(database)
    # os.chdir(base)

    # In[3]:

    today_file = arrow.now().format('YYYY-MM-DD')
    today_file
    myFormat = "%Y-%m-%d %H:%M:%S"
    current_datetime = datetime.datetime.now()
    today = current_datetime.strftime('%x')
    time = current_datetime.strftime('%X')
    date_time = current_datetime.strftime(myFormat)

    # In[4]:

    f1 = open('last_update.txt', 'r')
    last_update = f1.readline()
    print("Last update " + last_update)
    t1 = datetime.datetime.strptime(date_time, myFormat)
    t2 = datetime.datetime.strptime(last_update, myFormat)
    difference = t1 - t2
    print("It has been " + str(difference.seconds) + " seconds since the last update")

    f2 = open('last_update.txt', 'w')
    f2.write(date_time)  # python will convert \n to os.linesep
    f2.close()  # you can omit in most cases as the destructor will call it


def get_bref_advanced_stats(year):
    AS_master = "advanced_stats.xlsx"
    backup = "advanced_stats_bck.xlsx"
    # create a backup
    copy2(AS_master, backup)

    AS_df = pd.DataFrame()
    # gets the data
    url_template = "http://www.basketball-reference.com/leagues/NBA_{year}_advanced.html"

    url = url_template.format(year=year)  # get the url

    html = urllib.request.urlopen(url)  # get the html

    soup = BeautifulSoup(html, 'lxml')  # create our BS object
    column_headers = [th.getText() for th in
                      soup.findAll('tr', limit=3)[0].findAll('th')]

    # get our player data
    data_rows = soup.findAll('tr')[1:]
    player_data = [[td.getText() for td in data_rows[i].findAll('td')]
                   for i in range(len(data_rows))]

    # Turn yearly data into a DataFrame
    del column_headers[0]
    year_df = pd.DataFrame(player_data, columns=column_headers)

    # create and insert the Season column
    year_df.insert(0, 'Season', year)

    # Append to the big dataframe
    AS_df = AS_df.append(year_df, ignore_index=True)
    # Convert data to proper data types
    # AS_df = AS_df.convert_objects(convert_numeric=True)
    AS_df = AS_df.apply(pd.to_numeric, errors='ignore')
    # Get rid of the rows full of null values
    AS_df = AS_df[AS_df.Player.notnull()]
    # Replace NaNs with 0s
    AS_df = AS_df.dropna(axis=1, how='all')
    AS_df = AS_df.fillna(0)

    # dates when the ratings were pulled.
    AS_df['date'] = today
    # print(AS_df.head())

    # AS_df.to_csv(out_name, index=False)

    # Reads in the prior date AS

    try:
        ytd_AS_df = pd.read_excel(AS_master, sheet_name="AS")
    except:
        ytd_AS_df = AS_df
    # print(ytd_AS_df.shape)
    # print(AS_df.shape)

    # Drop any entries that match today's date in case this has already been run today

    ytd_AS_df.drop(ytd_AS_df[ytd_AS_df.date == today].index, inplace=True)
    # print(ytd_AS_df.shape)

    # combines and keeps the column order the same
    ytd_AS_df = ytd_AS_df.append(AS_df)[AS_df.columns.tolist()]

    # writes to excel
    writer_orig = pd.ExcelWriter(AS_master, engine='xlsxwriter')
    ytd_AS_df.to_excel(writer_orig, index=False, sheet_name="AS")
    writer_orig.save()
    print("Advanced Stats Updated")
    return ytd_AS_df


# In[6]:


def get_scores(year):  # Gets all the scores used in a given year

    # Gets all the months of play in the season

    # year = str("2018")
    # temp_df = pd.read_csv(str(2018) + "_schedule.csv", engine='python')
    # print(temp_df.head())
    # if (temp_df["pulled"] == today).any():
    #    return

    # Loads the main page and gets the monthly URLs
    url_template = "http://www.basketball-reference.com/leagues/NBA_{year}_games.html"

    url = url_template.format(year=year)  # get the url

    page = requests.get(url)
    try:
        page.raise_for_status()
    except Exception as exc:
        print('There was a problem: %s' % (exc))

    soup = bs4.BeautifulSoup(page.text, 'html.parser')
    links = soup.find_all(class_="filter")
    text = links[0].get_text()
    text = text.replace("\n\n", ".").replace("\n", "")
    text = text[1:]

    # Gets all the months that had games that year

    months = text.split(".")

    box_urls_year = []

    year_df = pd.DataFrame()
    ctr = 0

    # Gets the box-score links and the scores of the games for that month
    for current_month in months:
        box_urls = []
        current_month = current_month.lower()

        url_template = "http://www.basketball-reference.com/leagues/NBA_{year}_games-{month}.html"

        url = url_template.format(year=year, month=current_month)  # get the url

        # url = "http://www.basketball-reference.com/leagues/NBA_" + year + "_games-" + current_month + ".html"
        page = requests.get(url)
        try:
            page.raise_for_status()
        except Exception as exc:
            print('There was a problem: %s' % (exc))
        soup = bs4.BeautifulSoup(page.text, 'html.parser')

        # Gets URLs

        links = soup.select("#schedule a")
        for link in links:
            if (len(link.get('href'))) == 28:
                box_urls.append(link.get('href'))
        # box_df = pd.Series(box_urls)  # Moves the URLs for the month to a Pandas data series

        # Gets all the scores
        # Gets all the headers
        try:
            column_headers = [th.getText() for th in
                              soup.findAll('tr', limit=2)[0].findAll('th')]
        except:
            continue
        # Gets the data rows (including the game date)
        data_rows = soup.findAll('tr')[1:]
        # Gets the date of the game, and puts it into a list
        game_date = [[td.getText() for td in data_rows[i].findAll('th')]
                     for i in range(len(data_rows))]
        dates = []
        for game in game_date:
            dates.append(str(game[0]))
        # Gets the scores of the game, and puts it into a list

        game_data = [[td.getText() for td in data_rows[i].findAll('td')]
                     for i in range(len(data_rows))]

        game_data_02 = []  # create an empty list to hold all the data

        for i in range(len(data_rows)):  # for each table row
            game_row = []  # create an empty list for each pick/game

            # for each table data element from each table row
            for td in data_rows[i].findAll('td'):
                # get the text content and append to the game_row
                game_row.append(td.getText())

                # then append each pick/game to the game_data matrix
            game_data_02.append(game_row)

        col0 = column_headers[0]
        del (column_headers[0])
        # print (column_headers)
        # column_headers[4], column_headers[5] = "Box Scores", "OT"
        df = pd.DataFrame(game_data, columns=column_headers)
        # print("before adding the date, shape is of monthly chart is", df.shape)
        df[col0] = dates
        # print("after adding the date, shape is of monthly chart is", df.shape)
        try:
            ind = df[df.Date == "Playoffs"].index[0]
            box_urls.insert(ind, "Playoffs Begin")
        except:
            pass
        df.insert(0, 'Season', year)
        # print("after adding the season, the new shape is of monthly chart is", df.shape)
        while len(box_urls) - len(df.index) != 0:
            box_urls.append("No Game Yet")
        # print(len(box_urls), current_month, df.shape)
        df["URL"] = box_urls

        # Adds the current month to the full list of months

        year_df = year_df.append(df, ignore_index=True)
        # print("the final share of the monthly chart for " + current_month + " is ", df.shape)

    # print (year_df.shape)
    if int(year) < 2001:
        year_df.insert(1, "Start (ET)", "No times available before 2001")
        # print ("new shape of yearly chart is",year_df.shape)

    year_df['pulled'] = today

    # print("the shape for " + str(yr) + " is ")
    # print(year_df.shape)
    # sched_df = sched_df.append(year_df, ignore_index=True)

    # rename the Box Score and OT Columns

    year_df.rename(columns={list(df)[6]: 'Box/OT'}, inplace=True)

    # save the schedule
    year_df.to_csv(str(year) + "_schedule.csv")

    print("Scores Updated")
    return year_df


# In[7]:


def get_team_ratings(year):  # for each year

    # TR_df = pd.DataFrame()

    TR_master = "Team_Ratings.xlsx"
    backup = "Team_Ratings_bck.xlsx"
    # create a backup
    copy2(TR_master, backup)

    # gets the data from the web
    TR_url_template = "https://www.basketball-reference.com/leagues/NBA_{year}_ratings.html"
    url = TR_url_template.format(year=year)  # get the url

    html = urllib.request.urlopen(url)  # get the html

    soup = BeautifulSoup(html, 'lxml')  # create our BS object
    column_headers = [th.getText() for th in
                      soup.findAll('tr', limit=3)[1].findAll('th')]

    # get our team data
    data_rows = soup.findAll('tr')[1:]

    team_data = [[td.getText() for td in data_rows[i].findAll('td')]
                 for i in range(len(data_rows))]

    del column_headers[0]
    TR_df = pd.DataFrame(team_data, columns=column_headers)

    # TR_df = TR_df.convert_objects(convert_numeric=True)

    # Convert data to proper data types
    TR_df = TR_df.apply(pd.to_numeric, errors='ignore')

    # Appends the Daily team ratings to the Full List

    TR_df["Date"] = today

    temp_TR_df = pd.read_excel(TR_master, sheet_name="all")

    # Drop Any that match today's date
    temp_TR_df.drop(temp_TR_df[temp_TR_df.Date == today].index, inplace=True)
    # appends and keeps the column order the same
    temp_TR_df = temp_TR_df.append(TR_df)[TR_df.columns.tolist()]

    # writes to excel
    writer_orig = pd.ExcelWriter(TR_master, engine='xlsxwriter')
    temp_TR_df.to_excel(writer_orig, index=False, sheet_name="all")
    writer_orig.save()
    print("Team Ratings Updated")

    return temp_TR_df


# In[8]:


def get_game_logs(year):  # for each year
    GL_master = "game_logs.xlsx"
    backup = "game_logs_bck.xlsx"
    # create a backup
    copy2(GL_master, backup)

    ytd_df = pd.read_excel(GL_master, sheet_name="gl")

    rows = ytd_df.shape[0]
    print(rows)
    # rows=0
    url_template = "https://www.basketball-reference.com/play-index/tgl_finder.cgi?request=1&player=&match=game&lg_id=NBA&year_min={year}&year_max={year}&team_id=&opp_id=&is_range=N&is_playoffs=N&round_id=&best_of=&team_seed=&opp_seed=&team_seed_cmp=eq&opp_seed_cmp=eq&game_num_type=team&game_num_min=&game_num_max=&game_month=&game_location=H&game_result=&is_overtime=&c1stat=opp_off_rtg&c1comp=gt&c1val=-9&c2stat=fg&c2comp=gt&c2val=0&c3stat=tov_pct&c3comp=gt&c3val=-10&c4stat=&c4comp=&c4val=&order_by=date_game&order_by_asc=Y&offset={offset}"
    url = url_template.format(offset=rows, year=year)  # get the url
    print(url)

    html = urlopen(url)  # get the html

    soup = BeautifulSoup(html, 'lxml')  # create our BS object

    data_rows = soup.findAll('tr')[1:]

    team_data = [[td.getText() for td in data_rows[i].findAll('td')]
                 for i in range(len(data_rows))]

    if len(team_data) == 0:
        return ytd_df

    column_headers = ytd_df.columns.tolist()

    GL_df = pd.DataFrame(team_data)
    GL_df.drop(GL_df.columns[2], axis=1, inplace=True)

    GL_df = GL_df.apply(pd.to_numeric, errors='ignore')
    GL_df = GL_df.dropna(thresh=2)
    GL_df.columns = column_headers

    ytd_df = ytd_df.append(GL_df, ignore_index=True)
    # ytd_df = GL_df

    writer_orig = pd.ExcelWriter(GL_master, engine='xlsxwriter')
    ytd_df.to_excel(writer_orig, index=False, sheet_name="gl")
    writer_orig.save()
    return ytd_df


# In[9]:


def get_rpm():  # gets live rpm updates

    rpm_master = "rpm_2018.xlsx"
    ytd_rpm_df = pd.read_excel(rpm_master, sheet_name="rpm")

    ask = input("get rpm?")
    if len(ask) < 3:
        print("skip rpm")
        return ytd_rpm_df

    url_template = "http://www.espn.com/nba/statistics/rpm/_/page/{page}"
    rpm_df = pd.DataFrame()
    headers = ["RK", "NAME", "TEAM", "GP", "MPG", "ORPM", "DRPM", "RPM", "WINS"]
    for page in range(15):  # loops through rpm pages
        print(str(page + 1) + "\n")
        # retrievs rpm page
        url = url_template.format(page=page + 1)  # get the url
        try:
            html = urlopen(url)
        except:
            print("There are" + str(page) + "pages")
            break
        soup = BeautifulSoup(html, 'lxml')
        data_rows = soup.findAll('td')[9:]
        player_count = int(len(data_rows) / 9)

        page_data = []
        for i in range(player_count):
            player_data = []
            for stat in range(9):
                player_data.append(data_rows[i * 9 + stat].get_text())
            page_data.append(player_data)
            # print(page_data)
        page_df = pd.DataFrame(page_data, columns=headers)
        rpm_df = rpm_df.append(page_df, ignore_index=True)
    rpm_df["date"] = today
    print("done")
    # rpm_df.to_csv("rpm.csv", index=False)

    # Drop Any that match today's date
    ytd_rpm_df.drop(ytd_rpm_df[ytd_rpm_df.date == today].index, inplace=True)

    ytd_rpm_df = ytd_rpm_df.append(rpm_df)[rpm_df.columns.tolist()]

    writer_orig = pd.ExcelWriter(rpm_master, engine='xlsxwriter')
    ytd_rpm_df.to_excel(writer_orig, index=False, sheet_name="rpm")
    writer_orig.save()
    return ytd_rpm_df


# In[10]:


def get_bbm():
    dms_setup()
    bbm_master = "2019_bbm_minutes.xlsx"
    backup = "2019_bbm_minutes_bck.xlsx"
    # create a backup
    copy2(bbm_master, backup)

    # Gets the BBM projections for today
    daily_df = pd.read_csv(
        "https://basketballmonster.com/Daily.aspx?v=2&exportcsv=spCNg1wrgHj/doOsGLdsM5nui2/0UsfwJsQdj0iihOQ=")

    notes_df = pd.read_excel(
        "https://basketballmonster.com/Daily.aspx?exportxls=spCNg1wrgHj/doOsGLdsM5nui2/0UsfwJsQdj0iihOQ=",
        sheet_name="Sheet 1", parse_dates=['Date'])

    # Merge the notes and the daily minutes together

    daily_df["Name"] = daily_df["first_name"] + " " + daily_df["last_name"]
    temp_df = notes_df.copy()[["Name", "Inj", "Date"]]
    bbm_df = pd.merge(daily_df, temp_df, on="Name", how="left")

    # Appends the Daily BBM to the Full List

    bbm_df["date_pulled"] = today
    bbm_df["time_pulled"] = time
    today_game_date = bbm_df["Date"].iloc[0]

    # Read in the minutes so far this year and then making a copy??

    ytd_bbm_df = pd.read_excel(bbm_master, sheet_name="all")

    # writer_orig = pd.ExcelWriter(bbm_master, engine='xlsxwriter')
    # ytd_bbm_df.to_excel(writer_orig, index=False, sheet_name="all")
    # writer_orig.save()

    # Drop Any that match today's date
    ytd_bbm_df.drop(ytd_bbm_df[ytd_bbm_df.Date == today_game_date].index, inplace=True)

    # Append the new games to the ytd games, with the older version stripped.

    ytd_bbm_df = ytd_bbm_df.append(bbm_df, sort=True)[bbm_df.columns.tolist()]
    ytd_bbm_df["team_game_id"] = ytd_bbm_df["team"] + "_" + ytd_bbm_df["Date"].map(str)

    # Write the ytd minutes to a file

    writer_orig = pd.ExcelWriter(bbm_master, engine='xlsxwriter')
    ytd_bbm_df.to_excel(writer_orig, index=False, sheet_name="all")
    writer_orig.save()

    # Write a daily minutes copy for today's Sheet

    bbm_df.to_csv("today.csv", index=False)
    print("Daily Minutes Updated")

    # Return the full ytd list in order to create a master database
    return ytd_bbm_df