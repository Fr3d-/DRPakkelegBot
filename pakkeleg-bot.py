import requests
import time
import json
import re

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36"}

def getTimestamp():
	return int(time.time()*1000)

# takes 5 seconds to execute?
def DRLogin(email, password):
	payload = {
		"Email": email, 
		"Password": password,
		"Persistent": "false"
	}

	r = requests.post('https://www.dr.dk/login/', headers=headers, data=payload, allow_redirects=False, verify=False)
	if r.status_code == 302:
		return r
	else:
		return False

# takes 5 seconds to execute?
def DRGetToken(drSSOticket):
	cookies = {"dr-sso-ticket": drSSOticket}

	r = requests.get('https://www.dr.dk/login/api/me', headers=headers, cookies=cookies, verify=False)
	if r.status_code == 200:
		return r.json()["result"]["id"]
	else:
		return False
	
def getUserId(drSSOticket, userToken):
	cookies = {"dr-sso-ticket": drSSOticket}

	r = requests.get('https://www.dr.dk/pakkeleg/spil', headers=headers, cookies=cookies, verify=False)
	if r.status_code == 200:
		html = r.text
		pattern = "\"" + userToken + "\", (.*?)\)"
		result = re.search(pattern, html)

		if result is None: #This probably means we haven't setup a user.
			return saveAvatar(drSSOticket)

		return result.group(1)
	else:
		return False

def saveAvatar(drSSOticket):
	print("No existing avatar, creating new..")
	cookies = {"dr-sso-ticket": drSSOticket}
	params = {"ts": getTimestamp()}
	payload = {
		"Gender": "m",
		"Skin": 0,
		"Age": "child",
		"Name": password
	}

	r = requests.post('https://www.dr.dk/pakkeleg/avatar/saveavatar', params=params, headers=headers, data=payload, cookies=cookies, verify=False)
	return r.json()["UserId"]

def getInfo(drSSOticket, userToken, userId):
	cookies = {"dr-sso-ticket": drSSOticket}
	payload = {
		"id": userId, 
		"token": userToken,
	}

	r = requests.post("https://www.dr.dk/pakkeleg/avatar/infobyid", headers=headers, data=payload, cookies=cookies, verify=False)
	if r.status_code == 200:
		return r.json()

class DRPakkeleg:
	def __init__(self, drSSOticket, userToken, userId):
		self.cookie = {"dr-sso-ticket": drSSOticket}
		self.userinfo = {
			"Token": userToken,
			"UserId": userId
		}

		self.userToken = userToken
		self.userId = userId
		self.giftsToSteal = False
		self.quizCorrect = 0
		self.quizFalse = 0

	def getPresentToSteal(self, data):
		if not self.giftsToSteal:
			self.giftsToSteal = data["StealOptions"][0]

	def steal(self):
		if not self.giftsToSteal:
			pass#print("No gifts to steal.")

		params = {"ts": getTimestamp()}
		payload = self.userinfo
		payload["Action"] = "StealPresent"
		payload["Present"] = self.giftsToSteal

		#print("Stealing", self.giftsToSteal)
		r = requests.post("https://www.dr.dk/pakkeleg/play/game", headers=headers, data=payload, params=params, cookies=self.cookie, verify=False)
		self.giftsToSteal = False

	def startGame(self):
		params = {"ts": getTimestamp()}
		payload = self.userinfo
		payload["Action"] = "StartNewGame"

		r = requests.post("https://www.dr.dk/pakkeleg/play/game", headers=headers, data=payload, params=params, cookies=self.cookie, verify=False)
		return r.json()

	def rollDie(self):
		params = {"ts": getTimestamp()}
		payload = self.userinfo
		payload["Action"] = "RollDie"

		r = requests.post("https://www.dr.dk/pakkeleg/play/game", headers=headers, data=payload, params=params, cookies=self.cookie, verify=False)
		return r.json()
		#print("Rolled a", data["UserDie"])
		#print("NextAction", data["NextAction"])
		#print("Roundsleft", data["RoundsLeft"])

		#if data["UserDie"] == 6:
		#	getPresentToSteal(data)
		#	print("We're gonna steal", self.giftsToSteal)

	def unwrapPresents(self):
		params = {"ts": getTimestamp()}
		payload = self.userinfo
		payload["Action"] = "UnwrapPresents"

		r = requests.post("https://www.dr.dk/pakkeleg/play/game", headers=headers, data=payload, params=params, cookies=self.cookie, verify=False)
		return r.json()

	def resumeGame(self):
		params = {"ts": getTimestamp()}
		payload = self.userinfo
		payload["Action"] = "ResumeGame"

		r = requests.post("https://www.dr.dk/pakkeleg/play/game", headers=headers, data=payload, params=params, cookies=self.cookie, verify=False)
		return r.json()

	def getInfo(self):
		payload = {}
		payload["id"] = self.userinfo["UserId"]
		payload["token"] = self.userinfo["Token"]

		r = requests.post("https://www.dr.dk/pakkeleg/avatar/infobyid", headers=headers, data=payload, cookies=self.cookie, verify=False)
		return r.json()

	def gameLoop(self, data):
		nextAction = data["NextAction"]

		while(nextAction != "UnwrapPresents"):
			data = self.rollDie()

			if data["IsValid"] == False:
				if hasattr(data, 'StealOptions'):
					self.giftsToSteal = data["StealOptions"][0]
					self.steal()
				else:
					break

			else:
				#print("Got a ", data["UserDie"])

				if data["UserDie"] == 6:
					self.getPresentToSteal(data)
					self.steal()

				nextAction = data["NextAction"]

		data = self.unwrapPresents()
		if(data["IsValid"] == False):
			pass#print("Can't unwrap, probably no presents")
		else:
			if data["PresentsWon"]:
				pass#print(json.dumps(data["PresentsWon"], indent=4, sort_keys=True))
			else:
				pass#print("I have no idea what we won")



	def play(self):
		while True:
			data = self.getInfo()

			hasActiveGame = hasattr(data, 'HasActiveGame')
			gameCredits = data["GameCredits"]

			if hasActiveGame:
				#print("-->Resuming Game<--")
				data = self.resumeGame()
				self.gameLoop(data)
			else:
				if gameCredits > 0:
					#print("-->Starting Game<--")
					data = self.startGame()
					self.gameLoop(data)
				else:
					self.playQuiz()

					if self.getInfo()["GameCredits"] == 0:
						break

		print("-----------------------------------------------")
		print("Points earned today:", data["DailyPoints"])
		print("Points earned total:", data["TotalPoints"])
		print("Quiz:", self.quizCorrect, "/", self.quizFalse + self.quizCorrect)

	def getQuiz(self):
		params = {"ts": getTimestamp()}
		payload = self.userinfo
		payload["Action"] = "NewQuiz"

		r = requests.post("https://www.dr.dk/pakkeleg/play/quiz", headers=headers, data=payload, params=params, cookies=self.cookie, verify=False)
		return r.json()

	def answerQuiz(self, quizId, answerId):
		params = {"ts": getTimestamp()}
		payload = self.userinfo
		payload["Action"] = "AnswerQuiz"
		payload["QuizId"] = quizId
		payload["AnswerId"] = answerId

		r = requests.post("https://www.dr.dk/pakkeleg/play/quiz", headers=headers, data=payload, params=params, cookies=self.cookie, verify=False)
		return r.json()

	def getQuizHelp(self, data, quizQuestionId):
		#First we'll see if we have the answer locally
		correctAnswer = self.fileReadAnswer(quizQuestionId)

		if correctAnswer is not None:
			#print("Got answer from quiz.json")
			return correctAnswer

		if self.isBlacklisted(quizQuestionId):
			#print("Question is blacklisted therefore -->")
			return None

		#If not we'll try to find it on the web..
		link = data["Link"]
		answers = data["Answers"]
		content = requests.get(link).text

		temp = 0
		guess = None

		for answer in answers:
			#print(content.count(answer["Val"]))
			#print(temp)
			if content.count(answer["Val"]) > temp:
				temp  = content.count(answer["Val"])
				guess = answer["Id"]

		return guess

	def playQuiz(self):
		while True:
			data = self.getInfo()

			quizCredits = data["QuizCredits"]

			if quizCredits > 0:
				data = self.getQuiz()
				quizQuestionId = data["Question"]["Id"]
				answer = self.getQuizHelp(data, quizQuestionId)

				if answer is not None:
					#TODO: Learn to name variables
					didWeAnswerCorrectly = self.answerQuiz(quizQuestionId, answer)["Result"]["Answer"]
					#print("Answer is:", didWeAnswerCorrectly) # Prints whatever our guess was right/wrong

					if didWeAnswerCorrectly:
						self.fileAddAnswer(quizQuestionId, answer) # Add the correct answer to our list
						self.quizCorrect += 1
					else:
						self.quizFalse += 1
						self.fileAddBlacklist(quizQuestionId) # Blacklist 

				else:
					pass#print("Couldn't guess the quiz")

			else:
				#print("No more quiz credits")
				break

	def fileAddBlacklist(self, quizQuestionId):
		with open("blacklistquiz.json", "r") as json_file:
			json_data = json.load(json_file)

		if not str(quizQuestionId) in json_data:
			#print("Adding blacklist to quiz.json")
			json_data[str(quizQuestionId)] = True
		else:
			return

		with open("blacklistquiz.json", "w") as json_file:
			json_file.write(json.dumps(json_data))

	def isBlacklisted(self, quizQuestionId):
		with open("blacklistquiz.json", "r") as json_file:
			json_data = json.load(json_file)

			if str(quizQuestionId) in json_data:
				return True

		return False

	def fileAddAnswer(self, quizQuestionId, answer):
		with open("quiz.json", "r") as json_file:
			json_data = json.load(json_file)

		if not str(quizQuestionId) in json_data:
			#print("Adding answer to quiz.json")
			json_data[str(quizQuestionId)] = answer
		else:
			return

		with open("quiz.json", "w") as json_file:
			json_file.write(json.dumps(json_data))

	def fileReadAnswer(self, quizQuestionId):
		with open("quiz.json", "r") as json_file:
			json_data = json.load(json_file)

			if str(quizQuestionId) in json_data:
				return json_data[str(quizQuestionId)]

		return None

email = "" #Your email for your DR login
password = "" #Your password for your DR login

print(email, password)

drSSOticket = DRLogin(email, password).cookies["dr-sso-ticket"]
#print("drSSOticket =", drSSOticket)

userToken = DRGetToken(drSSOticket)
#print("userToken =", userToken)

userId = getUserId(drSSOticket, userToken)
#print("userId =", userId)

pakkeleg = DRPakkeleg(drSSOticket, userToken, userId)
pakkeleg.play()
