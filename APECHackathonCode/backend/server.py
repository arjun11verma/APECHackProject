from flask import Flask
from flask import request
from flask_cors import CORS, cross_origin
from ast import literal_eval

import os, mediacloud.api
from datetime import datetime, timedelta

import requests, json

import numpy as np
import torch
import torch.nn as nn
from torch.autograd import Variable

from newspaper import Article

app = Flask(__name__)

cors = CORS(app)

class LinearRegression(nn.Module):
    def __init__(self, input, output):
        super(LinearRegression, self).__init__()
        self.linear1 = nn.Linear(input, output)

    def forward(self, x):
        y_prediction = self.linear1(x)
        return y_prediction

@app.route('/analyzeCustomerData', methods=['POST', 'GET'])
def analyzeCustomerData():
    print(request.data)

    post_data = (literal_eval(request.data.decode('utf8')))
    data = post_data['data']

    print(data)

    y_data = []
    x_data = []
    xlen = 0
    return_data = []

    stopping_point = len(data) - 6 if len(data) > 6 else 0
    for i in range(stopping_point, len(data)):
        y_data.append([[float(data[i])]])
        x_data.append([[float(i+1-stopping_point)]])
        xlen += 1
    
    x_data = Variable(torch.tensor(x_data))
    y_data = Variable(torch.tensor(y_data))
    
    model = LinearRegression(1, 1)

    criterion = torch.nn.MSELoss(size_average = False) 
    optimizer = torch.optim.SGD(model.parameters(), lr = 0.01)
    for epoch in range(250): 
        optimizer.zero_grad() 
        predicted_number_of_customers = model.forward(x_data)
        loss = criterion(predicted_number_of_customers, y_data) 
        loss.backward()
        optimizer.step()
    
    for i in range(xlen - 1, xlen + 6):
        var = model(Variable(torch.tensor([[float(i)]]))).item()
        var = int(var)
        if(var < 0): var = 0
        return_data.append(var)
    
    print(xlen)
    print(x_data)
    print(y_data)
    print(return_data)

    return {'data': return_data}

@app.route('/covidData', methods=['POST', 'GET'])
def covidData():
    post_data = (literal_eval(request.data.decode('utf8')))

    country = post_data["country"]
    payload = {"lastdays": 14}
    r = requests.get('https://disease.sh/v3/covid-19/historical/{0}'.format(country), params=payload)
    json_data = json.loads(r.text)

    num = 0
    output = {}
    startdate = list(json_data["timeline"]["cases"].keys())[0]
    cases = json_data["timeline"]["cases"][startdate]
    deaths = json_data["timeline"]["deaths"][startdate]
    recovered = json_data["timeline"]["recovered"][startdate]
    for key in json_data["timeline"]["cases"].keys():
        output[num] = {"cases": json_data["timeline"]["cases"][key] - cases,
                       "deaths": json_data["timeline"]["deaths"][key] - deaths,
                       "recovered": json_data["timeline"]["recovered"][key] - recovered}
        cases = json_data["timeline"]["cases"][key]
        deaths = json_data["timeline"]["deaths"][key]
        recovered = json_data["timeline"]["recovered"][key]
        num += 1
    return output

def getNewsUrls(country):
    API_KEY = '25c5b9ccc207e7f56ce93f920a0253064a3b6c4fcbde0cedd7e5145d631c49c6'
    mc = mediacloud.api.MediaCloud(API_KEY)

    dateTimeObj = datetime.now()
    startsearch = (dateTimeObj - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stopsearch = dateTimeObj.strftime("%Y-%m-%dT%H:%M:%SZ")

    storylimit = 30
    tag_id_dict = {"MYS":38380297, "USA":34412234, "RUS":8878645, "CHN":34412193, "VNM":8878732,
    "THA":34412328, "SGP":34412474, "KOR":34412127, "JPN":34412056, "TWN":34412361, "PHL": 34412313,
    "BRN":34412241, "IDN":34412392, "AUS":34412282, "NZL":34412098, "CAN":34411583, "MEX": 34412427,
    "PER":34412158, "CHL":34412295}

    storylist = mc.storyList(
        solr_query='(title:covid OR title:coronavirus OR title:"covid-19") AND (title:food OR title:"small buisness" OR title:"Food Industry" OR title:"food regulations" OR title:"local buisness" OR title:"struggling buisness" OR title:resturant OR title:"local resturant" OR title:"food shipments" OR title:"food delivery") AND tags_id_media:{0}'.format(tag_id_dict[country]),
        solr_filter="publish_day:[{0} TO {1}]".format(startsearch, stopsearch),
        rows=storylimit)

    output = {}
    for index, value in enumerate(storylist):
        output[index] = value["url"]
    return output

@app.route('/getArticleInfo', methods=['POST', 'GET'])
def getArticleInfo():
    post_data = (literal_eval(request.data.decode('utf8')))
    country = post_data["country"]
    articleInfo = {}
    urls = getNewsUrls(country)
    count = 0
    goodCount = 0
    while count < len(urls):
        article = Article(urls[count])
        try:
            article.download()
            article.parse()
            if (isinstance(article.publish_date, datetime)):
                date = article.publish_date.strftime('%m/%d/%Y')
            else:
                date = article.publish_date
            authors = []
            for x in article.authors:
                if len(x.split(" ")) == 2:
                    authors.append(x)
            if not authors: 
                authors[0] = "No Author"
            if date == None:
                date = "No Date"
            if article.top_image == None:
                article.top_image = "No imageURL"
            if article.title == None:
                article.title = "No title"
            if count != 0 and goodCount != 0 and urls[count] == articleInfo[goodCount - 1]["url"]:
                print("Inside if statement")
                raise Exception
            articleInfo[goodCount] = {"authors": authors, "date": date, "url": urls[count],
            "imageURL": article.top_image, "title": article.title}
            count = count + 1
            goodCount = goodCount + 1
        except Exception as e:
            print(e)
            count = count + 1 
            print("bad article")
    return articleInfo


app.run()
