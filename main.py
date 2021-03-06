import json
from slacker import Slacker
from flask import Flask, request, make_response, send_from_directory
import numpy as np
import pandas as pd
from server.db import dbModule as db
from sentence_transformers import SentenceTransformer, util
import os
import scipy.stats


token =
slack = Slacker(token)

# 전역변수 선언
status_value = False
top_results =''

def reconstruct_dataframe(json_df):
    questions = []
    results = []
    id_temp = json_df.loc[0, "질문 메세지 id"]
    url = 'http://168.131.30.128:8080/server/data/rsc/'

    question_file = json_df.loc[0, "질문자 file"]
    question_df = json_df.loc[0, "질문내용"]
    if question_file != '':
        question_file = url + question_file
        question_df += '\n' + question_file

    result_file = json_df.loc[0, "답변자 file"]
    result_df = "답변(" + json_df.loc[0, '답변자 이름'] + ")" + '\n' + json_df.loc[0, "답변내용"]
    if result_file != '':
        result_file = url + result_file
        result_df += '\n' + result_file

    for i in range(1, len(json_df)):
        if id_temp != json_df.loc[i, "질문 메세지 id"]:
            questions.append(question_df)

            result_file = json_df.loc[i-1, "답변자 file"]
            result_df = "질문(" + json_df.loc[i - 1, '질문자 이름'] + ')' + '\n' + question_df + "\n\n\n" +result_df
            if result_file != '':
                result_file = url + result_file
                result_df += '\n' + result_file

            results.append(result_df)
            result_df = ''

        id_temp = json_df.loc[i, "질문 메세지 id"]

        question_file = json_df.loc[i, "질문자 file"]
        question_df = json_df.loc[i, "질문내용"]
        if question_file != '':
            question_file = url + question_file
            question_df += '\n' + question_file

        result_file = json_df.loc[i, "답변자 file"]
        result_df = result_df + '\n\n' + "답변(" + json_df.loc[i, '답변자 이름'] + ")" + '\n' + str(json_df.loc[i, "답변내용"])
        if result_file != '':
            result_file = url + result_file
            result_df += '\n' + result_file

    reconstruct_df = pd.DataFrame({"질문내용": questions, "결과 값": results})
    return reconstruct_df

# 데이터 로드
database = db.Database()
qa_sql = "SELECT * FROM leedo.qa_dataset"
ig_sql = "SELECT * FROM leedo.imground"
dataset_qa = database.execute_all(qa_sql)
dataset_ig = database.execute_all(ig_sql)
dataset_qa = pd.DataFrame(dataset_qa)
dataset_ig = pd.DataFrame(dataset_ig)

columns = ['QAID','질문 날짜','답변 날짜',
           '질문 메세지 id','답변 메세지 id',
           '질문자 id', '답변자 id',
           '질문자 이름', '답변자 이름',
           '질문내용', '답변내용',
           '질문자 file', '답변자 file',
           '채널']
dataset_qa.columns = columns
#dataset_ig = pd.read_json('/Users/sinjaeug/Desktop/프로젝트/2020_2학기 프로젝트/Leedo Dataset/imground_dataset.json')
#dataset_qa = pd.read_json('/Users/sinjaeug/Desktop/프로젝트/2020_2학기 프로젝트/Leedo Dataset/qa_dataset.json')
dataset_qa = reconstruct_dataframe(dataset_qa)

# 데이터 로드 후 index 순서대로 정렬
# 코드작성하기!!!!!!!
##########


# Corpus and Name 셋 세팅
# imground_part
corpus_ig = dataset_ig['content'].values.tolist()
corpus_ig = [word.replace('\xa0', ' ') for word in corpus_ig]
name_ig = dataset_ig['name'].values.tolist()
name_ig = [word.replace('\xa0',' ') for word in name_ig]

# qa_part
corpus_qa = [str(x) for x in dataset_qa['질문내용']]
corpus_answer = [str(x) for x in dataset_qa['결과 값']]

attachment_answer_json = {
	"blocks": [
		{
			"type": "actions",
			"elements": [
				{
					"type": "static_select",
					"placeholder": {
						"type": "plain_text",
						"text": "유사한 질문 목록"
					},
					"options": [
						{
							"text": {
								"type": "plain_text",
								"text": "1"
							},
							"value": "0"
						},
						{
							"text": {
								"type": "plain_text",
								"text": "2"
							},
							"value": "1"
						},
						{
							"text": {
								"type": "plain_text",
								"text": "3"
							},
							"value": "2"
						},
						{
							"text": {
								"type": "plain_text",
								"text": "4"
							},
							"value": "3"
						},
						{
							"text": {
								"type": "plain_text",
								"text": "5"
							},
							"value": "4"
						}
					],
					"action_id": "actionId-3"
				}
			]
		}
	]
}


# embedding 모듈 load


# 1.2 ver
model_path = 'distiluse-base-multilingual-cased-v2'
embedder = SentenceTransformer(model_path)
# embedder = SentenceTransformer('distiluse-base-multilingual-cased-v2') # 1.1ver
# embedder = SentenceTransformer('xlm-r-bert-base-nli-stsb-mean-tokens')


# corpus Embedding
corpus_embeddings_qa = embedder.encode(corpus_qa, convert_to_tensor=True)
corpus_embeddings_ig = embedder.encode(corpus_ig, convert_to_tensor=True)


app = Flask(__name__)


def get_answer():
    return "EA (EconoAsistant) 사용법 \n\n1. Q&A 검색엔진 \n\n - 키워드를 통해 분야에 대해 알아봐요 - \n   " \
           "느낌표 1개 (!)를 붙이고 키워드나 문구를 \n   적으면 관련된 과거 에코노인들의 정보를 찾아드려요!.\n\n2. " \
           "I'm Ground \n\n - 키워드를 통해 에코노인을 알아봐요 - \n   느낌표 2개 (!!)를 붙이고 키워드나 " \
           "문구를 \n   적으면 관련된 사람을 알려드립니다."


def event_handler(event_type, slack_event):
    print("3번오류")
    if event_type == "app_mention":
        channel = slack_event["event"]["channel"]
        text = get_answer()
        slack.chat.post_message(channel, text)
        return make_response("앱 멘션 메시지가 보내졌습니다.", 202,)

    if event_type == "message":
        channel = slack_event["event"]["channel"]
        print(channel)
        message_query = slack_event["event"]["text"]
        text = ''
        if message_query[1] == '!':
            text = im_ground(message_query)
            print(text)
            slack.chat.post_message(channel, text)
        else:
            text = question_answer(message_query)
            print(text)
            slack.chat.post_message(channel, attachments=[text])

        return make_response("앱 멘션 메시지가 보내졌습니다.", 202,)

    message = "[%s] 이벤트 핸들러를 찾을 수 없습니다" % event_type
    return make_response(message, 200, {"X-Slack-No-Retry": 1})


def query_confirm(query_input):
    global status_value
    if query_input[0:1] == "!" or query_input[0:2] == "!!":
        status_value = True
        return True
    else:
        status_value = False
        return False


# !를 제거 하는 함수
def delete_exclamation_mark(query_input):
    if query_input[0:1] == "!":
        return query_input[1:]
    elif query_input[0:2] == "!!":
        return query_input[2:]


def question_answer(query_input):
    global top_results
    query = delete_exclamation_mark(query_input)

    # query embedding
    query_embedding = embedder.encode(query, convert_to_tensor=True)

    # cosine_similarity 계산
    cos_scores = util.pytorch_cos_sim(query_embedding, corpus_embeddings_qa)[0]

    # We use np.argpartition, to only partially sort the top_k results
    top_k = 5
    top_results = np.argpartition(-cos_scores, range(top_k))[0:top_k]

    read_text_to_json = json.dumps(attachment_answer_json)
    read_json = json.loads(read_text_to_json)
    for i, idx in enumerate(top_results[0:top_k]):
        temp_str = str(i+1) + "번 " + corpus_qa[idx].strip()
        temp_str = temp_str[0:30] + "(%2.f%%)" % (cos_scores[idx]*100)
        read_json["blocks"][0]['elements'][0]['options'][i]['text']['text'] = temp_str
    return read_json


def im_ground(query_input):
    query = delete_exclamation_mark(query_input)

    # query embedding
    query_embedding = embedder.encode(query, convert_to_tensor=True)

    # cosine_similarity 계산
    cos_scores = util.pytorch_cos_sim(query_embedding, corpus_embeddings_ig)[0]

    # 상위 다섯개 출력 (10개 여분으로 세팅하고, 중복 제거)

    top_k = 10
    top_results_ig = np.argpartition(-cos_scores, range(top_k))

    name_overlap = []

    number = 1
    result =''
    for i, idx in enumerate(top_results_ig[0:top_k]):
        if number > 5:
            break
        if cos_scores[idx] > 0.3:
            if not name_ig[idx] in name_overlap:
                temp = str(i + 1) + "번 " + name_ig[idx].strip() + ', ' + corpus_ig[idx].strip() + '\n'
                result = result + str(temp)
                name_overlap.append(name_ig[idx].strip())
                number += 1

    return result


@app.route("/slack", methods=["GET", "POST"])
def hears():
    slack_event = json.loads(request.data)
    print("1번 오류")
    if "challenge" in slack_event: # 슬랙이 정상적으로 웹서버가 동작하는지 확인하는 과정
        return make_response(slack_event["challenge"], 200,
                             {"content_type": "application/json"})

    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        message_query = slack_event["event"]["text"]
        if query_confirm(message_query):
            return event_handler(event_type, slack_event)

        if event_type == "app_mention":
            return event_handler(event_type, slack_event)

        return make_response("슬랙 요청에 이벤트가 없습니다", 404,
                             {"X-Slack-No-Retry": 1})
    return make_response("슬랙 요청에 이벤트가 없습니다", 404,
                         {"X-Slack-No-Retry": 1})


@app.route("/", methods=["GET", "POST"])
def index():
    return "Hello World"

@app.route('/server/data/rsc/<file_dir>')
def download_file(file_dir):
    path = './server/data/rsc/' + file_dir
    filename = os.listdir(path)[0]
    return send_from_directory(path, filename,as_attachment=True)

@app.route("/slack/message_actions", methods=["POST"])
def message_actions():
    # 리퀘스트 파징
    form_json = json.loads(request.form["payload"])

    print("2번오류")
    # 선택한 값이 버튼일 때
    selection = form_json["actions"][0]["selected_option"]["value"]
    slack.chat.update(form_json["channel"]["id"], form_json["container"]["message_ts"], corpus_answer[top_results[int(selection)]])

    return make_response("", 200)


if __name__ == '__main__':
    app.run('0.0.0.0', port=8080)
