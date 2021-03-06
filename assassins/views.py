from random import choice
import simplejson
import urllib
import urllib2

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.db.models import Sum

from models import *
from utils import *

class Config(object):
    MAX_MELEE_KILL_DIST = 2
    MAX_BOMB_KILL_DIST = 10

def revive_player(request):
    uid = request.POST["fbid"]
    execute_revive(uid)
    return HttpResponse("revive player success")

def revive_all(request):
    execute_revive_all()
    return HttpResponse("revive all success")

def report_kill(request):
    possible_messages = ["{1} just wiped the floor with {0}!",
                         "{0} was strolling down the street waiting for when {1} blasted him in the FACE!!! H-H-H-HEADSHOT",
                         "{0} ran into a pole and died. {1} was there to laugh at him.",
                         "{1} just cut venture funding from {0}, who eventually died.",
                         "{1} offered {0} the blue pill or the red pill. {0} took the one made from rat poison."]
    assassin_id, lat, lng, target_id, tar_lat, tar_long = extract_location_data(request)
    if Assassin.objects.get(facebook_id=assassin_id).alive == True:
        execute_kill(assassin_id)
        assassin_name = Assassin.objects.get(facebook_id=assassin_id).first_name
        victim_name = Assassin.objects.get(facebook_id=target_id).first_name
        message = choice(possible_messages).format(victim_name, assassin_name)
        post_to_feed(message, assassin_id, target_id)
        return HttpResponse("kill")
    else:
        return HttpResponse("dead")

def confirm_melee_kill(request):
    possible_messages = ["{1} clubbed {0} upside the head for massive damage. WHACK! WHAMMO! BOOM!",
                        "{1} knew that the first rule of hitting with a club is that one don't talk about hitting with a club. The second is to hit {0} when he isn't paying attention. BAM! BOOM! WHOOSH!",
                        "{1} inducted {0} into the clubbed club, clubbing {0} for massive damage. BONK! BARF! BIFF!",
                        "Even though {1} gave {0} a knuckle sandwich, {0} still seemed hungry, so {1} gave him a club sandwich with a club for enormous damage. WHAMMO! SMACK! WHACK!",
                        "{1} goes clubbing with {0}, and I don't mean the dancing kind"]

    assassin_id, lat, lng, target_id, tar_lat, tar_long = extract_location_data(request)
    if Assassin.objects.get(facebook_id=target_id).alive == True:
        dist = get_distance(lat, lng, tar_lat, tar_long)
        if dist < Config.MAX_MELEE_KILL_DIST:
            execute_kill(assassin_id)
            assassin_name = Assassin.objects.get(facebook_id=assassin_id).first_name
            victim_name = Assassin.objects.get(facebook_id=target_id).first_name
            message = choice(possible_messages).format(victim_name, assassin_name)
            post_to_feed(message, assassin_id, target_id)
            return HttpResponse("kill")
    else:
        return HttpResponse("dead")
    return HttpResponse("nokill")

def assign_target(request):
    player = request.POST['player_id']
    target = request.POST['target_id']
    add_target(player, target)
    return HttpResponse("target_assigned")

def plant_bomb(request):
    assassin_id, lat, lng, target_id, tar_lat, tar_long = extract_location_data(request)
    bomb_type = request.POST['type']
    if bomb_type in ('mine','sticky'):
        add_bomb(assassin_id, target_id, bomb_type, lat, lng, 99)
    return HttpResponse("success")

def extract_location_data(request):
    assassin_id = request.POST['fbid']
    lat = request.POST['lat']
    lng = request.POST['lng']
    assassin = Assassin.objects.get(facebook_id=assassin_id)
    target_id = assassin.target_id
    if target_id:
        target = Assassin.objects.get(facebook_id=target_id)
        tar_lat, tar_long = get_location(target_id)
        return assassin_id, lat, lng, target_id, tar_lat, tar_long
    return assassin_id, lat, lng, target_id, 0, 0

def get_distance(lat1, lng1, lat2, lng2):
    return (((float(lat1)-float(lat2))**2)+((float(lng1)-float(lng2))**2))**0.5

def poll_location(request):
    players = Player.objects.all()
    JSON_string = "["
    for player in players:
        JSON_string += "{\"fbid\":\""+player.facebook_id+"\","
        JSON_string += "\"name\":\""+player.first_name+"\","
        JSON_string += "\"photo\":\""+player.photo+"\","
        JSON_string += "\"lat\":\""+str(player.location_lat)+"\","
        JSON_string += "\"lng\":\""+str(player.location_long)+"\"},"
    if JSON_string != "[":
        JSON_string = JSON_string[:-1]
    JSON_string += "]"
    return HttpResponse(JSON_string)

def get_posts(request):
    post_sets = get_feed()
    JSON_string = "["
    for post_set in post_sets:
        JSON_string += "{\"from\":\"" + post_set.from_user + "\","
        JSON_string += "\"to\":\"" + post_set.to_user + "\","
        JSON_string += "\"time\":\"" + str(post_set.create_time) + "\","
        JSON_string += "\"message\":\"" + post_set.message + "\"},"
    if JSON_string != "[":
        JSON_string = JSON_string[:-1]
    JSON_string += "]"
    return HttpResponse(JSON_string)

def get_statistics(request):
    total_players = str(Assassin.objects.count())
    total_survivors = str(Assassin.objects.filter(alive=True).count())
    body_count = str(Assassin.objects.filter(alive=False).count())
    fatalities = str(Assassin.objects.aggregate(Sum('kills'))["kills__sum"])
    start_time = "4:13 AM"
    JSON_string = "{\"total_players\":\""+total_players+"\",\"total_survivors\":\""+total_survivors+"\",\"body_count\":\""+body_count+"\",\"fatalities\":\""+fatalities+"\",\"start_time\":\""+start_time+"\"}"
    return HttpResponse(JSON_string)

def update_player_location(request):
    assassin_id, lat, lng, target_id, tar_lat, tar_long = extract_location_data(request)
    update_location(assassin_id, lat, lng)
    if Assassin.objects.get(facebook_id=assassin_id).alive == True:
        bombs = get_bombs_on_me(assassin_id)
        for bomb in bombs:
            if get_distance(lat, lng, bomb.bomb_lat, bomb.bomb_long) < Config.MAX_BOMB_KILL_DIST:
                victim_name = Assassin.objects.get(facebook_id=assassin_id).first_name
                assassin_name = Assassin.objects.get(target_id=assassin_id).first_name
                assassin_id = Assassin.objects.get(target_id=assassin_id).facebook_id
                execute_kill(assassin_id)
                message = "BOOM! "+assassin_name+" just killed "+victim_name+"!"
                bomb.delete()
                post_to_feed(message, assassin_id, target_id)
                return HttpResponse("kill")
    else:
        return HttpResponse("dead")
    return HttpResponse("nokill")

def new_game(request):
    add_session(request.POST['name'],
                request.POST['description'],
                request.POST['uid'])

def add_new_player(request):
    fbid = request.POST['fbid']

    uri = "http://graph.facebook.com/" + str(fbid)

    result = simplejson.load(urllib.urlopen(uri))

    uid = result['id']
    f_name = result['first_name']
    l_name = result['last_name']
    gender = result['gender']
    username = result['username']
    picture = "http://graph.facebook.com/" + username + "/picture"

    new_player, victim = add_player(uid, "auth token", f_name, l_name, gender, picture)
    response = ", ".join([f_name + " " + l_name, picture, victim.first_name + " " + victim.last_name, victim.photo])
    return HttpResponse(response)

def add_player_to_game(request):
    player = Assassin.objects.get(facebook_id=uid)
    game = AssassinSession.objects.get(session_id=game_id)
    update_session(player, game)

def home(request):
    players = Player.objects.all()
    locations = []
    for player in players:
        location = {}
        location['fbid'] = player.facebook_id
        location['name'] = player.first_name
        location['photo'] = player.photo
        location['lat'] = str(player.location_lat)
        location['long'] = str(player.location_long)
        locations.append(location)
    posts_sets = get_feed(5)
    posts = []
    for post_set in posts_sets:
        post = {}
        post['fbid'] = post_set.facebook_id
        post['name'] = post_set.first_name
        post['photo'] = post_set.photo
        post['lat'] = str(post_set.location_lat)
        post['lng'] = str(post_set.location_long)
        posts.append(post)
    return render_to_response('home.html', RequestContext(request,{"posts":posts, "locations":locations}))

def dashboard(request):
    return render_to_response('dashboard.html')

def get_leader_board(request):
    return HttpResponse("{\"")
