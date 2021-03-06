from __future__ import with_statement
from flask import Flask, render_template, request, session, g, redirect, url_for, \
	 abort, flash
from flask.ext.classy import FlaskView, route
import fnmatch, re, json, getTOI

class toi(FlaskView):
	# todo for this function
	#	+ can enter 3 digit times
	#	+ send old values to form for checkbox 
	#	+ (use wtf-forms) 
	#	+ get if team is home or away
	#	+ prettier box to report numbers.
	def index(self):
		urlgid = None
		urlper = None
		team1 = None
		team1roster = []
		team2 = None
		team2roster = []
		message = None

		gameidForm = ""
		timeidForm = "20:00"

		return render_template('toi.html', team1=team1, team2=team2,
								team1roster=team1roster, team2roster=team2roster,
								error = message, gameid=gameidForm, timerem=timeidForm)

	def post(self):
		urlgid = None
		urlper = None
		team1 = None
		team1roster = []
		team2 = None
		team2roster = []
		message = None

		gameidForm = ""
		timeidForm = "20:00"

		gyear = request.form['gyear']
		gid = request.form['gameid']
		gameid = str(gyear) + '0' + str(gid)
		period = request.form['period']
		time = request.form['time']

		mins = time[:2]
		secs = time[3:5]

		# check if gid is in db
		cur = g.db.execute('SELECT * FROM shifts WHERE gameid=%s', [gameid])

		if not gyear.isdigit() or int(gyear) not in range(2007, 2014):
			message = "Game year is not valid."
		elif not gid.isdigit() or len(gid) != 5:
			message = "Game ID is not valid."
		elif period not in ['1','2','3', '4']:
			message = "Period is not valid."
		elif not re.match(r'^\d\d:\d\d$', time):
			message = "Time is not in valid format"
		elif int(mins)*60 + int(secs) > 1200: 
			message = "Time is too high."
		else:
			if cur.fetchone() is None:
				#message = "This game id does not exist in our database."
				getTOI.getGameTOI(gameid)
			# fails to grab anything?  Handle this
			# SELECT * FROM pbp WHERE cast(timedown as integer) >= 1166 AND gid=30151 AND period = 1 ORDER BY gnumber DESC LIMIT 1;
			# SELECT * FROM shifts WHERE gameid = 2012020123 AND shift_start >= 1000 AND shift_end < 1000 AND period = 2 ORDER BY playerteamname, playernumber+0;
			sql = "SELECT * FROM shifts WHERE gameid = %s AND shift_start >= %s AND shift_end < %s AND period = %s ORDER BY playerteamname, playernumber+0"
			queryGameID = int(mins)*60 + int(secs)
			params = [int(gameid), queryGameID, queryGameID, int(period)]
			cur = g.db.execute(sql, params)
			fetchd = cur.fetchall()
			if fetchd != []:
				# turn fetchd into a list, do stuff easier here
				team1 = fetchd[0][5]
				team2 = ""
				for player in fetchd:
						if player[5] == team1:
							team1roster.append(player[3])
						else:
							team2roster.append(player[3])
							team2 = player[5].title()
				# make fancy lists
				team1 = team1.title()
				team1roster = ' <br />'.join(team1roster)
				team2roster = ' <br />'.join(team2roster)
			else:
				message = "Nothing found for these values"
		gameidForm = str(gid)
		timeidForm = time
		return render_template('toi.html', team1=team1, team2=team2,
								team1roster=team1roster, team2roster=team2roster,
								error = message, gameid=gameidForm, timerem=timeidForm)

	@route('/onice/')
	def onice(self):
		oGid = request.args.get('gameid')
		exits = request.args.get('exits')
		onIcePlayers = {}
		# check if game id is real
		if not str(oGid).isdigit() or len(str(oGid)) != 10:
			return "Game ID is invalid"
		# parse TOI if need to
		cur = g.db.execute('SELECT COUNT(*) FROM shifts WHERE gameid = %s', [oGid])
		results = cur.fetchone()
		if results[0] == 0:
			getTOI.getGameTOI(oGid)

		for e in exits.split(","):
			onIcePlayers[e] = []
			eData = e.split(":")
			period = eData[0]
			tRemaining = eData[1]
			team = eData[2]
			location = 'h' if str(team) == '1' else 'v'
			# find the players for this period, time, team
			sql = "SELECT * FROM shifts WHERE gameid = %s AND shift_start >= %s AND shift_end < %s AND period = %s AND location = %s ORDER BY playerteamname, playernumber+0"
			params = [oGid, tRemaining, tRemaining, period, location]
			cur = g.db.execute(sql, params)
			pInExits = cur.fetchall()
			for player in pInExits:
				onIcePlayers[e].append( player[4] )
			print "%s - %s" % (period, tRemaining)
		return json.dumps(onIcePlayers)
		# return the dictionary

	@route('/roster/<int:gameid>/<fetch>')
	def rosterRedo(self, gameid, fetch=None):
		if fetch == "true":
			# delete from this game id
			g.db.execute('DELETE FROM shifts WHERE gameid = %s', [gameid])
		return redirect(url_for('toi:roster',gameid=gameid))

	@route('/roster/<int:gameid>')
	def roster(self, gameid):
		# not in game?  parse in
		cur = g.db.execute('SELECT COUNT(*) FROM shifts WHERE gameid = %s', [gameid])
		results = cur.fetchone()
		if results[0] == 0:
			getTOI.getGameTOI(gameid)
		cur = g.db.execute('SELECT playernumber, playername, location FROM shifts WHERE gameid = %s GROUP BY playername ORDER BY location, playernumber+0;', [gameid])
		players = cur.fetchall()
		home = {}
		away = {}
		for data in players:
			indata = "".join(i for i in data[1] if ord(i) < 128)
			if data[2] == 'h':
				home[data[0]] = data[1]
			else:
				away[data[0]] = data[1]
		data = {}
		data['h'] = home
		data['v'] = away
		return json.dumps(data)


	@route('/api/', endpoint='apibase')
	@route('/api/<int:urlgid>/')
	@route('/api/<int:urlgid>/<int:urlper>/')
	def APIInstruction(self, urlgid=None, urlper=None):
		return render_template('toi-instructions.html')

	@route('/api/<int:urlgid>/<int:urlper>/<int:urltrem>')
	def toiapp(self, urlgid=None, urlper=None, urltrem=None):
		# check if urlgid is a digit and 10 
		error = True
		message = "API"
		team1 = []
		team2 = []
		team1name = "team1"
		team2name = "team2"
		if len(str(urlgid)) != 10:
			message = "Not a valid game ID"
		elif urlper not in range(1,7):
			message = "Period is not valid"
		elif urltrem not in range(0,1201):
			message = "Time is not valid."
		else:
			# check if gameid is in db
			# check if anything with selected data
			# return what we have
			sql = "SELECT * FROM shifts WHERE gameid = %s AND shift_start >= %s AND shift_end < %s AND period = %s ORDER BY playerteamname, playernumber+0"
			params = [urlgid, urltrem, urltrem, urlper]
			cur = g.db.execute(sql, params)
			fetchd = cur.fetchall()
			if fetchd != []:
				# turn fetchd into a list, do stuff easier here
				team1name = fetchd[0][5]
				for player in fetchd:
						if player[5] == team1name:
							team1.append(player[3])
						else:
							team2.append(player[3])
							team2name = player[5].title()
				# make fancy lists
				team1name = team1name.title()
				error = False
				message = "ACK"
			else:
				message = "Nothing found for these values"
		return json.dumps({'error' : error, 'message' : message,
							'team1name' : team1name, 'team2name' : team2name,
							'team1' : team1, 'team2' : team2})