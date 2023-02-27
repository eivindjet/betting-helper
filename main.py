from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from webdriver_manager.chrome import ChromeDriverManager

import time
from bs4 import BeautifulSoup

import pandas as pd

import pymysql


driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
club_links = ["https://www.premierleague.com/clubs?se=489", "https://www.uefa.com/uefachampionsleague/clubs/"]

alle_lag = [[], []]

#Premier League
driver.get(club_links[0])

ready = str(input("Ready: "))
if ready == "y":
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
    time.sleep(5)

html = driver.page_source
soup = BeautifulSoup(html, "html.parser")

for s in soup.find_all("li"):
    for k in s.find_all("a"):
        if "/clubs/" in k["href"]:
            alle_lag[0].append(k["href"].replace("overview", "stats?se=489"))
    
alle_lag[0].remove(alle_lag[0][-1])


#Champions League
driver.get(club_links[1])

ready = str(input("Ready: "))
if ready == "y":
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
    time.sleep(5)

html = driver.page_source
soup = BeautifulSoup(html, "html.parser")

c = 0
for s in soup.find_all("div", class_="team team-is-club"):
    for k in s.find_all("a"):
        if "/clubs/" in k["href"] and c < 32:
            alle_lag[1].append(k["href"] + "statistics")
            c += 1
            
stats = [[], []]
i = 0
for a in alle_lag[0]:
    driver.get("https://www.premierleague.com" + a)
    time.sleep(2)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    lag = {}
    lag["name"] = soup.find("h1").text
    for s in soup.find_all("span", class_="stat"):
        temp = s.text.split("\n")
        temp = temp[0].split(" ")
        if len(temp) > 2:
            for t in temp:
                if t == "" or t == "\n":
                    temp.remove(t)
            num = temp[-1]
            num = num.replace("%", "")
            num = num.replace(",", "")
            stat = " ".join(temp[0:len(temp)-2])
            try:
                lag[stat] = float(num)
            except ValueError:
                pass

    stats[0].append(lag)
    
for a in alle_lag[1]:
    driver.get("https://www.uefa.com/" + a)
    time.sleep(2)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    lag = {}
    for v in soup.find_all("span", class_="team-name pk-d-sm--none"):
        temp = str(v).split(">")
        lag["name"] = temp[1][:-6]
        print(lag["name"])
        
    p = soup.find("pk-donut-chart")
    lag["Matches played"] = float(p["total-value"])
    lag["wins"] = float(p["series"][1])
    lag["losses"] = float(p["series"][-2])
    
    for s in soup.find_all("pk-num-stat-item", class_="hydrated"):
        temp = []
        for r in s.find_all("div"):
            temp.append(r.text)
        stat = temp[1]
        num = temp[0]
        num = num.replace("%", "")
        num = num.split("/")
        lag[stat] = float(num[0])

    stats[1].append(lag)
    
pl_df = pd.DataFrame.from_dict(stats[0])
cl_df = pd.DataFrame.from_dict(stats[1][-32:])

pl_cols = pl_df.columns
cl_cols = cl_df.columns

alle_lag_df = [pl_df, cl_df]
cols = [pl_cols, cl_cols]
weights = [pl_weights, cl_weights]
for j in range(len(alle_lag_df)):
    for l in range(len(alle_lag_df[j])):
        score = 0.0
        for i in range(2, len(cols[j])):
            score += float(alle_lag_df[j][l:l+1][cols[j][i]])*float(weights[j][i-2])

        score = score/alle_lag_df[j][l:l+1]["Matches played"]
        #print("{}: {} in  {}".format(alle_lag_df[j][l:l+1][cols[j][0]], score, alle_lag_df[j][l:l+1][cols[j][1]]))
        alle_lag_df[j].loc[l, "score"] = float(score)
        
df = alle_lag_df

def h_bonus(df):
    return (df["score"].max() - df["score"].mean())/3
  
import requests


# An api key is emailed to you when you sign up to a plan
# Get a free API key at https://api.the-odds-api.com/
API_KEY = '06b346055f463fba1fd8aa76aa65bc0b'

SPORTS = ['soccer_epl', 'soccer_uefa_champs_league'] # use the sport_key from the /sports endpoint below, or use 'upcoming' to see the next 8 games across all sports

REGIONS = 'eu' # uk | us | eu | au. Multiple can be specified if comma delimited

MARKETS = 'h2h' # h2h | spreads | totals. Multiple can be specified if comma delimited

ODDS_FORMAT = 'decimal' # decimal | american

DATE_FORMAT = 'iso' # iso | unix

BOOKMAKERS = 'unibet_eu'

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#
# First get a list of in-season sports
#   The sport 'key' from the response can be used to get odds in the next request
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

"""sports_response = requests.get(
    'https://api.the-odds-api.com/v4/sports', 
    params={
        'api_key': API_KEY
    }
)


if sports_response.status_code != 200:
    print(f'Failed to get sports: status_code {sports_response.status_code}, response body {sports_response.text}')

else:
    print('List of in season sports:', sports_response.json())"""



# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
#
# Now get a list of live & upcoming games for the sport you want, along with odds for different bookmakers
# This will deduct from the usage quota
# The usage quota cost = [number of markets specified] x [number of regions specified]
# For examples of usage quota costs, see https://the-odds-api.com/liveapi/guides/v4/#usage-quota-costs
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

all_odds_json = []
for SPORT in SPORTS:
    odds_response = requests.get(
        f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds',
        params={
            'api_key': API_KEY,
            'regions': REGIONS,
            'markets': MARKETS,
            'oddsFormat': ODDS_FORMAT,
            'dateFormat': DATE_FORMAT,
            'bookmakers': BOOKMAKERS,
        }
    )

    if odds_response.status_code != 200:
        print(f'Failed to get odds: status_code {odds_response.status_code}, response body {odds_response.text}')

    else:
        odds_json = odds_response.json()
        #print('Number of events:', len(odds_json))
        all_odds_json.append(odds_json)

        # Check the usage quota
        #print('Remaining requests', odds_response.headers['x-requests-remaining'])
        #print('Used requests', odds_response.headers['x-requests-used'])
        
import datetime

d = datetime.datetime.now()
m = ""
if d.month < 10:
    m = "0" + str(d.month)
DATE = str(d.year) + m + str(d.day)
#print(DATE)

url = "https://livescore6.p.rapidapi.com/matches/v2/list-by-date"

querystring = {"Category":"soccer","Date":{DATE},"Timezone":"-7"}

headers = {
	"X-RapidAPI-Key": "7e64a90858msh4e02aa98930b046p139d9djsn6ba1adf31afe",
	"X-RapidAPI-Host": "livescore6.p.rapidapi.com"
}

response = requests.request("GET", url, headers=headers, params=querystring)

h = response.json()

T = [[], []]
if h["Stages"][0]["CompN"] == "Premier League" and h["Stages"][0]["CompD"] == "England":
        #T1 = {h["Stages"][i]["Events"][0]["T1"][0]["Nm"]:h["Stages"][0]["Events"][0]["Tr1"]}
        #T2 = {h["Stages"][i]["Events"][0]["T2"][0]["Nm"]:h["Stages"][0]["Events"][0]["Tr2"]}
    for i in range(len(h["Stages"][0]["Events"])):
        T[0].append([{"Team1":h["Stages"][0]["Events"][i]["T1"][0]["Nm"], "Team2":h["Stages"][0]["Events"][i]["T2"][0]["Nm"]}])
if h["Stages"][0]["CompN"] == "Champions League" and h["Stages"][0]["CompD"] == "UEFA":
        #T1 = {h["Stages"][i]["Events"][0]["T1"][0]["Nm"]:h["Stages"][0]["Events"][0]["Tr1"]}
        #T2 = {h["Stages"][i]["Events"][0]["T2"][0]["Nm"]:h["Stages"][0]["Events"][0]["Tr2"]}
    for i in range(len(h["Stages"][0]["Events"])):
        T[1].append([{"Team1":h["Stages"][0]["Events"][i]["T1"][0]["Nm"], "Team2":h["Stages"][0]["Events"][i]["T2"][0]["Nm"]}])
        
def predict(df, T, DATE):
    for z in range(len(T)):
        for i in range(len(T[z])):
            hjemmelag = T[z][i][0]["Team1"].replace("&", "and")
            bortelag = T[z][i][0]["Team2"].replace("&", "and")
            hjemmelag = hjemmelag.replace("Munich", "München")
            bortelag = bortelag.replace("Munich", "München")
            hjemmelag = hjemmelag.replace("-", " ")
            bortelag = bortelag.replace("-", " ")
            temph = hjemmelag.split(" ")
            tempb = bortelag.split(" ")
            h_score = 0.0
            b_score = 0.0
            for team in df[z]["name"]:
                tempT = team.split(" ")
                if tempT[-1] == temph[-1] or tempT[0] == temph[0]:
                    h_score = float(df[z][df[z]["name"]==team].score) + float(h_bonus(df[z]))
                elif tempT[-1] == tempb[-1] or tempT[0] == tempb[0]:
                    b_score = float(df[z][df[z]["name"]==team].score)

                    
            #print(h_score)
            #print(b_score)
            prediction = ""

            if abs(h_score - b_score) <= (df[z]["score"].max() - df[z]["score"].min())/4:
                prediction = "Draw"
            elif h_score > b_score:
                prediction = hjemmelag
            else:
                prediction = bortelag

            if hjemmelag == "AFC Bournemouth":
                hjemmelag = "Bournemouth"
            elif bortelag == "AFC Bournemouth":
                bortelag = "Bournemouth"

                
            #print(hjemmelag)
            #print(bortelag)
            vinner_odds = 0.0
            for k in range(len(all_odds_json)):
                for g in range(len(all_odds_json[k])):
                    if len(all_odds_json[k][g]["bookmakers"]) > 0:
                        if all_odds_json[k][g]["home_team"] == hjemmelag and all_odds_json[k][g]["away_team"] == bortelag:
                            for j in range(3):
                                if all_odds_json[k][g]["bookmakers"][0]["markets"][0]["outcomes"][j]["name"] == prediction:
                                    vinner_odds = all_odds_json[k][g]["bookmakers"][0]["markets"][0]["outcomes"][j]["price"]

            connection = pymysql.connect(host="153.92.220.1", user="u679803740_eivjet", passwd="BI=Ru3D2i%hlnS!4", database="u679803740_database1")
            cursor = connection.cursor()

            gamedate = DATE[6:] + "." + DATE[4:6] + "." + DATE[:4]
            sql = "insert into predictions (Hjemmelag, Bortelag, Prediction, Odds, Date) values (%s, %s, %s, %s, %s);"
            cursor.execute(sql, (hjemmelag, bortelag, prediction, str(vinner_odds), gamedate))
            connection.commit()

            cursor.close()
            
predict(df, T, DATE)
