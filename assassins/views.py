import simplejson
import urllib
import urllib2

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

from girl.config import Config
from models import *
from utils import *

def report_kill(request):
    assassin_id, lat, lng, target_id, tar_lat, tar_long = extract_location_data(request)
    kill(target_id)
    assassin_name = Assassin.objects.get(facebook_id=assassin_id).first_name
    victim_name = Assassin.objects.get(facebook_id=target_id).first_name
    message = assassin_name+" just killed "+victim_name+"!"
    post_to_feed(message, assassin_id, target_id)
    return HttpResponse("kill")

def confirm_melee_kill(request):
    assassin_id, lat, lng, target_id, tar_lat, tar_long = extract_location_data(request)
    dist = get_distance(lat, lng, tar_lat, tar_long)
    if dist < Config.MAX_MELEE_KILL_DIST:
        kill(target_id)
        message = "MELEE! "+assassin_name+" just killed "+victim_name+"!"
        post_to_feed(message, assassin_id, victim_name)
        return HttpResponse("kill")
    else:
        return HttpResponse("nokill")

def confirm_bomb_kill(request):
    assassin_id, lat, lng, target_id, tar_lat, tar_long = extract_location_data(request)

def assign_target(request):
    player = request.POST['player_id']
    target = request.POST['target_id']
    add_target(player, target)
    return HttpResponse("target_assigned")

def plant_bomb(request):
    assassin_id, lat, lng, target_id, tar_lat, tar_long = extract_location_data(request)
    bomb_type = request.POST['type']
    if bomb_type in ('sticky', 'mine'):
        add_bomb(assassin_id, target_id, bomb_type, lat, lng, seconds)

def extract_location_data(request):
    assassin_id = request.POST['fbid']
    lat = request.POST['lat']
    lng = request.POST['lng']
    assassin = Assassin.objects.get(facebook_id=assassin_id)
    target_id = assassin.target_id
    target = Assassin.objects.get(facebook_id=target_id)
    tar_lat, tar_long = get_location(target_id)
    return assassin_id, lat, lng, target_id, tar_lat, tar_long

def get_distance(lat1, lng1, lat2, lng2):
    return sqrt(((lat1-lat2)**2)+((lng1-lng2)**2))

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
    post_sets = get_feed(5)
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

def update_player_location(request):
    assassin_id = request.POST['fbid']
    lat = request.POST['lat']
    lng = request.POST['lng']
    update_location(assassin_id, lat, lng)
    #bombs = Bombs.objects.filter(target_id=assassin_id)
    #for bomb in bombs:
        #b_lat
        #if get_distancebomb.bomb_lat,
    return HttpResponse("Location updated")

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

    add_player(uid, "auth token", f_name, l_name, gender, picture)
    return HttpResponse(request.POST['fbid'])

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
