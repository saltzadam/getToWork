# some exploration with MBTA GFTS and googlemaps

import requests
import json
import csv 
import datetime
import calendar
import time

from fuzzywuzzy import process
from fuzzywuzzy import fuzz
from dateutil import parser

import copy

class Step:
    # try to use GTFS codes
    def __init__(self,origin_station_name,origin_station_id,destination_station_name,destination_station_id,route_id,step_type,step_time):
        self.init = origin_station_name
        self.init_id = origin_station_id
        self.final = destination_station_name
        self.final_id = destination_station_id
        self.route_id = route_id # 0 for walking
        self.type = step_type
        self.step_time = step_time
    def __str__(self):
        return "Step: " + self.init + " to " + self.final + " via " + self.type + "."

def get_stops_data():
    with open('MBTA_GTFS/stops.txt',newline='') as csvfile:
        for stop_line in  csv.reader(csvfile):
            yield stop_line
stops_data = list(get_stops_data())
def get_trips_data():
    with open('MBTA_GTFS/trips.txt',newline='') as csvfile:
        for trip_line in csv.reader(csvfile):
            yield trip_line
trips_data = list(get_trips_data())
def get_routes_data():
    with open('MBTA_GTFS/routes.txt',newline='') as csvfile:
        for route_line in csv.reader(csvfile):
            yield route_line
routes_data = list(get_routes_data())
def get_routes_pattern_data():
    with open('MBTA_GTFS/route_patterns.txt') as csvfile:
        for route_pattern in csv.reader(csvfile):
            yield route_pattern
def get_stop_times_data():
    with open('MBTA_GTFS/stop_times.txt') as csvfile:
        for stop_time in csv.reader(csvfile):
            yield stop_time
def get_routes(gmaps_directions):
    """ takes gmap data in the form of json
        returns a list of routes """
    return gmaps_directions['routes']

def get_steps(gmaps_route):
    """ takes gmap route
        returns a list of steps """
    return gmaps_route['legs'][0]['steps']

# get my mbta api private key
with open("/home/adam/mbtaapikey") as mbtaapifile:
    mbtaapikey = mbtaapifile.read().split('\n')[0]

# get my google api private key
with open("/home/adam/gapikey") as gapifile:
    gapikey = gapifile.read().split('\n')[0]

# takes epoch time, returns epoch time at end of MBTA service that "day"
# TODO: work out what end of day means.  For now, just add a day
# (for that, don't need to use time.gmtime -- just add 60 * 60 * 24)
def end_of_day(a_time):
    return (a_time + 60 * 60 * 24)

def yesterday(a_time):
    return (a_time - (60 * 60 * 24))
# interesting: mktime will deal with the 32nd day of July!

# step is a Step
# queue_time is a time in epoch (?) when you start waiting for step
# returns (start_time,end_time,ellapsed_time, benchmark_time)
def time_step(queue_time,step):
    realtime_api_key = mbtaapikey
    if step.type == "WALKING":
        pass
    else:
        if step.type == "HEAVY_RAIL":
            #route_url_id = heavy_rail_name_dict[step.route_id]
            route_url_id = step.route_id
        elif step.type == "SUBWAY":
            route_url_id = step.route_id
        else:
            route_url_id = step.route_id
        req_url = "http://realtime.mbta.com/developer/api/v2.1/traveltimes?api_key=" + mbtaapikey + "&format=json&from_stop=" + step.init_id + "&to_stop=" + step.final_id + "&from_datetime=" + str(queue_time) + "&to_datetime=" + str(end_of_day(queue_time)) + "&route=" + route_url_id
        #print(req_url)
        req_json = json.loads(requests.get(req_url).text)
        #print(req_json)
        earliest_arrival = min([trip for trip in req_json['travel_times']],key=lambda lst: lst['arr_dt'])
        return (earliest_arrival['dep_dt'],earliest_arrival['arr_dt'],earliest_arrival['travel_time_sec'],earliest_arrival['benchmark_travel_time_sec'])
        
def arrival_time(dept_time, route):
    try:
        total_time = sum(time_route(dept_time,route))
    except ValueError:
        raise
    except KeyError:
        raise
    print(total_time)
    return (int(dept_time) + int(total_time))

def time_route(queue_time,route):
    time_ellapsed = 0
    times = []
    for step in route['legs'][0]['steps']:
        try:
            parsed = parse_step(step)
        except ValueError:
            raise
        except KeyError:
            raise
        if parsed.type == "WALKING":
            times.append(parsed.step_time)
        else:
            times.append(int(time_step(int(queue_time) + time_ellapsed,parsed)[2]))    
    return times

def fancy_classify_step(gmaps_step):
    """ takes a step, e.g. from get_steps
        returns "BUS #", "GL", "OL", "CR Haverill-IB", etc."""
    mode = gmaps_step['travel_mode']
    if mode == "WALKING":
        return "WALKING"
    elif mode == "TRANSIT":
        details = gmaps_step['transit_details']
        type = details['line']['vehicle']['type']
        return type
    """    if type == "BUS":
            bus_num = details['line']['short_name']
            return "BUS " + bus_num
        elif ((type == "SUBWAY") or (type == "TRAM")):
            name = details['line']['name']
            return light_rail_name_dict[name]
        elif type == "HEAVY_RAIL":
            name = details['line']['name']
            return heavy_rail_name_dict[name]
        else: raise ValueError('not a recognized TRANSIT mode')"""



def find_stop(stop_name,headsign,line_type,line=''):
    candidate_stops = set([stop[0] for stop in stops_data if stop[2] == stop_name and stop[1] != ''])
    #print(stop_name + ', ' + headsign + ', ' + line_type)
    if len(candidate_stops) == 1:
        c = candidate_stops.pop()
        return terminal_dict.get(c, c)
    else:
#        if line_type[0:3] == 'BUS':
         relevant_trip_ids = set([trip[2] for trip in trips_data if trip[0] == line and trip[3] == headsign])
         relevant_stops = set([stop_time[3] for stop_time in get_stop_times_data() if stop_time[0] in relevant_trip_ids])
         hopefully_only_one = [candidate for candidate in relevant_stops if candidate in candidate_stops]
         try:
             c = hopefully_only_one.pop()
             return terminal_dict.get(c,c)
         except IndexError: 
            if not line:
               preprocessed = {stop[0] : stop[3] for stop in stops_data}
               (_,_,c) = process.extractOne(stop_name + " - " + headsign, preprocessed,scorer=fuzz.partial_ratio)
            else:
                preprocessed = {stop[0] : stop[3] for stop in stops_data}
                (_,_,c) = process.extractOne(stop_name + " - " + line + "-" + headsign, preprocessed,scorer=fuzz.token_sort_ratio)
                return terminal_dict.get(c,c)

def parse_step(gmaps_step):
    step_type = fancy_classify_step(gmaps_step)
    if step_type == "WALKING":
        return Step("","","","",0,step_type,gmaps_step['duration']['value'])
    else: 
        departure_name = gmaps_step['transit_details']['departure_stop']['name']
        arrival_name = gmaps_step['transit_details']['arrival_stop']['name']
        # hopefully [routes][0][legs][0][steps][n]['transit_details']['line']['name']
        # matches MBTA route_ids
        pre_type = gmaps_step['transit_details']['line']['vehicle']['type'] 
        if pre_type in ['SUBWAY', 'HEAVY_RAIL']:
            route_short_name = gmaps_step['transit_details']['line']['name']
        elif pre_type == 'TRAM':
            route_short_name = light_rail_name_dict[gmaps_step['transit_details']['line']['name']]
        else:
            try: 
                route_short_name = gmaps_step['transit_details']['line']['short_name']
            except KeyError:
                raise
        route_headsign = gmaps_step['transit_details']['headsign']
        try:
            finded = next(iter([route for route in get_routes_data() if (route[0] == route_short_name or route[3] == route_short_name)]))
            route_name = finded[0]
        except StopIteration: 
            if route_name_short == 'Peter Pan':
                raise ValueError
            routes_name_set = set()
            for route in routes_data:
                routes_name_set.add(route[3])
            print ("Can't find a route named " + route_short_name + ".  Please pick one of the options below.")
            near_matches = [x[0] for x in process.extract(route_short_name,routes_name_set, limit = 4)] # obviously this block and the one in the next function should be abstracted out
            route_name = pick_list(near_matches)
        # just added [0]
        #print([departure_name,route_headsign,step_type,route_short_name])
        departure_id = find_stop(departure_name, route_headsign, step_type, route_short_name)
        arrival_id = find_stop(arrival_name, route_headsign, step_type, route_short_name)
        return Step(departure_name, departure_id, arrival_name, arrival_id, route_name, step_type,0)


"""def name_to_gtfs(name):
    stops_data_clone = stops_data[:]
    try: 
        finded = next(iter([stop for stop in stops_data_clone if stop[2] == name and stop[0][0].isdigit()])) # break this up over multiple lines
        return finded[0]
    except StopIteration: # this means an exact match was not found
        stops_name_set = set() 
        for stop in stops_data_clone:
            stops_name_set.add(stop[2])
        print ("Can't find a stop named " + name + ".  Please pick one of the options below.")
        near_matches = [x[0] for x in process.extract(name,stops_name_set, limit = 4)]
        return pick_list(near_matches)
        # looks for the closest
        # match to name in stops_name_list (using?)"""
        
def pick_list(options):
    i = 1
    for opt in options:
        print (str(i) + ") " + opt)
        i +=1
    choice = input("Pick: ")
    def validate(inpt,times):
        try:
            inpt_num = int(inpt)
            return options[inpt_num - 1]
        except: 
            if times >= 3:
                print("Well now you're just horsing around.")
            else: 
                new_inpt = input("Please pick from the options above:")
                times +=1
                validate(new_inpt,times)
    return validate(choice,0)
            
light_rail_name_dict = {'Green Line D': 'Green-D',
                        'Green Line C': 'Green-C', 
                        'Green Line B': 'Green-B', 
                        'Green Line E': 'Green-E',
                        'Red Line': 'Red',
                        'Orange Line': 'Orange',
                        'Blue Line': 'Blue'}

heavy_rail_name_dict = {
        'Fairmount Line': 'CR-Fairmount',
        'Fitchburg Line': 'CR-Fitchburg',
        'Foxboro (Special Events)': 'PATS',
        'Framingham/Worcester Line': 'CR-Worcester',
        'Franklin Line': 'CR-Franklin',
        'Greenbush Line': 'CR-Greenbush',
        'Haverhill Line': 'CR-Haverhill',
        'Kingston/Plymouth Line': 'CR-Kingston',
        'Lowell Line': 'CR-Lowell',
        'Middleborough/Lakeville Line': 'CR-Middleborough',
        'Needham Line': 'CR-Needham',
        'Newbury/Rockport Line': 'CR-Newburyport',
        'Providence/Stoughton Line': 'CR-Providence'
        }


# some terminal stations do not have reliable performance info for departures
# so queries come up as empty, very bad
# shift to nearest station going the right direction
# TODO: add warning when user searches for one of these
terminal_dict = {
        '70106' : '70110' # Boston College -> South Street
        }

def main():
    print("Time to get to work!")
    destination = input("Where would you like to go? ")
    origin = input("Where are you starting from? ")
    dept_time_string = input('What time of day are you planning to leave?  For example, 8:00AM.  Leave empty for "right now."')
    if dept_time_string == "":
        dept_time_time = int(time.time())
    else:
        dept_time_time = parser.parse(dept_time_string).timestamp()
    
    if destination == "": destination = "Porter Square"
    if origin == "": origin = "Boston College"

    dept_times = [yesterday(dept_time_time)]
    for i in range(1,7): # get departure times for last seven days
        dept_times.append(yesterday(dept_times[-1]))
    dept_times = map(str,dept_times)
    
    lengths = []
    for dept_time in dept_times:
        direction_url = 'https://maps.googleapis.com/maps/api/directions/json?origin=' + origin + '&destination=' + destination + '&alternatives=true&mode=transit&departure_time=' + dept_time + '&key=' + gapikey
        #print(direction_url)
   
        directions = json.loads(requests.get(direction_url).text)
        day_lengths = []
        for route in directions['routes'][0:5]:  # TODO: assumes first five routes are best
            try:
                a_time = arrival_time(dept_time,route)
                day_lengths.append(a_time)
            except ValueError:
                pass
            except KeyError:
                pass
        lengths.append(day_lengths)
    print(lengths)




if __name__ == "__main__":
    # execute only if run as a script
    main()

