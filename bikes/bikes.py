import requests
import location
from math import cos, asin, sqrt, isclose
import appex, ui, os
import resource
import time
from pprint import pprint
import json
import datetime


home = [
  (
    "Flamborough Street, Limehouse",
    "BikePoints_480",
  ),
  (
    "Salmon Lane, Limehouse",
    "BikePoints_542",
  ),
  (
    "Westferry DLR, Limehouse",
    "BikePoints_510",
  )
]

work = [
  (
    "Breams Buildings, Holborn",
    "BikePoints_84",
  ),
  (
    "Carey Street, Holborn",
    "BikePoints_232",
  ),
  (
    "New Fetter Lane, Holborn",
    "BikePoints_546",
  ),
]
{
  "Bouverie Street, Temple": "BikePoints_27",
  "Holborn Circus, Holborn": "BikePoints_66",
  "Hatton Garden, Holborn": "BikePoints_67",
  #"Arundel Street, Temple": "BikePoints_79",
  #"Strand, Strand": "BikePoints_174",
  "Chancery Lane, Holborn": "BikePoints_82"
}

def distance(lat1, lon1, lat2, lon2):
  p = 0.017453292519943295     #Pi/180
  a = 0.5 - cos((lat2 - lat1) * p)/2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2
  return 12742 * asin(sqrt(a)) #2*R*asin...

def get_bike_data():
  url = 'https://api.tfl.gov.uk/BikePoint'
  r = requests.get(
    url,
    headers={'Cache-Control': 'no-cache'}
    )
  for station in r.json():
    yield station

def get_my_location():
  location.start_updates()
  time.sleep(0.1)
  loc = location.get_location()
  location.stop_updates()
  return loc['latitude'],loc['longitude']

def get_simple_station_data():
  d=get_bike_data()
  stations = {}
  for s in d:
    n = s['commonName']
    stations[n] = (
      s['id'],
      s['lat'],
      s['lon']
    )
  return stations
    
def write_simple_file():
  with open('bikes.json','w') as f:
    f.write(
      json.dumps(
        get_simple_station_data(),
        indent=2
      )
    )
    
def get_station_by_name(name):
  n = name.lower()
  for station in get_bike_data():
    if n in station['commonName'].lower():
      return station

def get_close_stations(
    dist=0.007, # in degrees of lat/lon
    looking_for='NbEmptyDocks',
    lat=None,lon=None
  ):
  data = get_bike_data()
  if lat is None or lon is None:
    lat, lon = get_my_location()
  stations = {}
  for station in data:
    la = station['lat']
    if not isclose(
        la,
        lat,
        abs_tol=dist
      ):
      continue
    lo = station['lon']
    if not isclose(
        lo,
        lon,
        abs_tol=dist
      ):
      continue
    n = station['commonName']
    d = {}
    for p in (
        'id',
        'lat',
        'lon'
      ):
      d[p]=station[p]
    stations[n]=d
  return stations
    
def find_nearby_stations(
    dist=0.007, # in degrees of lat/lon
    looking_for='NbEmptyDocks',
    lat=None,lon=None
  ):
  data = get_bike_data()
  if lat is None or lon is None:
    lat, lon = get_my_location()
  stations = []
  for station in data:
    la = station['lat']
    if not isclose(
        la,
        lat,
        abs_tol=dist
      ):
      continue
    lo = station['lon']
    if not isclose(
        lo,
        lon,
        abs_tol=dist
      ):
      continue
    name = station[
      'commonName'
    ]
    
    props = station[
      'additionalProperties'
    ]
    for prop in props:
      k = prop['key']
      if k != looking_for:
        continue
      v = prop['value']
      if int(v) == 0:
        continue

      a = abs(la-lat)
      b = abs(lo-lon)
      c = sqrt(a*a+b*b)
      
      d = distance(
        lat,
        lon,
        la,
        lo
      )
      d = int(d*1000)
      stations.append(
        {
          'name': name,
          'distance': d,
          looking_for: v,
        }
      )
  return sorted(
    stations, 
    key=lambda k: k['distance']
  )
  
class BikeView(ui.View):
  def __init__(self, *args, **kwargs):
    super().__init__(self, *args, **kwargs)
    button_style = {
      'background_color': (0, 0, 0, 0.05), 'tint_color': 'black', 
      'font': (
        'HelveticaNeue-Light', 
        24
      ),
      'corner_radius': 3
    }
    self.bounds = (0, 0, 500, 600)
    self.bikes_button = ui.Button(
      title='Find Bikes', 
      action=self.handle_click, 
      **button_style
    )
    self.add_subview(
      self.bikes_button
    )
    self.space_button = ui.Button(
      title='Find Spaces', 
      action=self.handle_click, 
      **button_style
    )
    self.add_subview(
      self.space_button
    )
    self.display_view = dv = ui.ScrollView(
      background_color=(.54, .94, 1.0, 0.2)
    )
    self.display_label = ui.Label(
    #self.display_label = ui.WebView(
      frame=dv.bounds.inset(0, 8), 
      flex='wh', 
      text='Begin Search', 
      alignment=ui.ALIGN_CENTER,
      number_of_lines=0
    )
    self.display_label.font = ('HelveticaNeue-Light', 18)
    self.display_view.add_subview(
      self.display_label
    )
    self.add_subview(self.display_view)
    self.l = l = ui.ListDataSource(
      items=['work','home']
    )
    self.t =t= ui.TableView()
    t.data_source=l
    self.add_subview(t)
    
  def layout(self):
    bh = self.height/4
    bw = self.width/2
    self.bikes_button.frame = ui.Rect(
      0, bh*3, bw, bh
    ).inset(1, 1)
    self.space_button.frame = ui.Rect(
      bw, bh*3, bw, bh
    ).inset(1, 1)
    self.display_view.frame = (
      0, 0, self.width, bh*3
    )
    self.auto_search()
    
  def auto_search(self):
    '''if its pre-midday and i'm close to home, set 'home' and find bikes. if i'm close to work, set work and find spaces. if its past midday and i'm close to work, find bikes. if i'm close to home, find spaces. else, do nothing.
    '''
    t = 'Find Bikes'
    global home, work
    s = home
    dt = datetime.datetime.now()
    athome = closer_to_home_than_work()
    ismorning = (5 < dt.hour < 12)
    if athome and ismorning:
      self.desc='home, morning: bikes'
      #print('home, morning')
    elif (not athome) and ismorning:
      self.desc='work, morning: spaces'
      #print('work, morning')
      t = 'Find Spaces'
      s = work
    elif athome and (not ismorning):
      self.desc='home, evening: spaces'
      self.t.selected_row = (0, 1)
      t = 'Find Spaces'
    elif (not athome) and (not ismorning):
      self.desc='work, evening: bikes'
      s = work
    else:
      return
    self._clicked = False
    self.find(t,s)

  def handle_click(self, sender):
    stats = work
    _,r = self.t.selected_row
    if r:
      stats=home
    self._clicked = True
    self.find(sender.title, stats)

  def find(self, title, stats):
    t = title
    l = {
      'Find Bikes':'NbBikes',
      'Find Spaces':'NbEmptyDocks'
    }
    label = self.display_label
    label.text = 'Searching...'
    #results = [t]
    if self._clicked:
      self.desc = t
    label.text = self.desc.capitalize()
    for name,sid in stats:
      try:
        b,s = get_bikes_and_spaces(sid)
      except Exception as e:
        try:
          time.sleep(0.1)
          b,s = get_bikes_and_spaces(sid)
        except Exception as e:
          continue
      #n = get_num(sid, term=l[t])
      label.text += '\n%s: %s/%s' % (name,b,b+s)
      #results.append(
        #'%s: %s/%s' % (name,b,b+s)
        #'<font size="13"><p>%s\n%s: <b>%s</b>/%s</p></font>' % (t,name,b,b+s)
      #)
      if t == 'Find Bikes':
        n = b
      elif t == 'Find Spaces':
        n = s
      if n > 5:
        break
    #label.text = '\n'.join(results)
    #label.load_html('\n'.join(results))
    '''
    rsrc = resource.RLIMIT_DATA
    #soft,hard=resource.getrlimit(rsrc)
    resource.setrlimit(rsrc,
    (1024*1024,15*1024*1024)
    )
    stations = find_nearby_stations(
      dist=0.008, # in degrees of lat/lon
      looking_for=l[t]
    )
    f = t.replace('Find ', '')
    s = '\n'.join(
      ['%s: %s %s, %sm'%(
        st['name'],
        st[l[t]],
        f,
        st['distance']
        )
        for st in stations
      ]
    )
    label.text = s
    '''

def get_bikes_and_spaces(sid):
  url = 'https://api.tfl.gov.uk/Place/'
  url += sid #'BikePoints_480'
  r = requests.get(
    url,
    headers={'Cache-Control': 'no-cache'}
  )

  dd = r.json()
  p = dd.get('additionalProperties')
  if p is None:
    return
  for o in p:
    k = o['key']
    v = o['value']
    if k == 'NbBikes':
      bikes = int(v)
    if k == 'NbEmptyDocks':
      spaces = int(v)
  return bikes,spaces
      
def get_num(sid,term='NbBikes'):
  url = 'https://api.tfl.gov.uk/Place/'
  url += sid#'BikePoints_480'
  r = requests.get(
    url,
    headers={'Cache-Control': 'no-cache'}
  )
  d = r.json()
  p = d['additionalProperties']
  for o in p:
    if o['key'] == term:#'NbEmptyDocks':
      v = o['value']
      return int(v)
    
def get_lookup_dict():
  stations = {}
  for s in get_bike_data():
    n = s['commonName']
    i = s['id']
    p = s['additionalProperties']
    d = {}
    d['name'] = n
    stations[i] = d
    for o in p:
      v = o['value']
      k = o['key']
      if k=='NbBikes':
        d['bikes'] = v
      elif k=='NbEmptyDocks':
        d['spaces'] = v
  return stations
  
def get_station_ids_close_to(lat,lon):
  data = get_bike_data()
  stations = {}
  for station in data:
    la = station['lat']
    if not isclose(
        la,
        lat,
        abs_tol=0.004
      ):
      continue
    lo = station['lon']
    if not isclose(
        lo,
        lon,
        abs_tol=0.004
      ):
      continue
    name = station[
      'commonName'
    ]
    i = station['id']
    stations[name] = i
  return stations
    
def main():
  # Optimization: Don't create a new view if the widget is already showing the BikeView.
  widget_name = __file__ + str(os.stat(__file__).st_mtime)
  widget_view = appex.get_widget_view()
  if widget_view is None or widget_view.name != widget_name:
    widget_view = BikeView()
    widget_view.name = widget_name
    appex.set_widget_view(widget_view)

work_loc = {
  'lat' : 51.515667,
  'lon' : -0.111743
}
work_ll = work_loc['lat'],work_loc['lon']
home_loc = {
  'lat': 51.509980,
  'lon': -0.030770
}

def closer_to_home_than_work():
  lat, lon = get_my_location()
  wlo = work_loc['lon']
  hlo = home_loc['lon']
  return abs(wlo-lon)>abs(hlo-lon)

  
def get_station_names():
    lat, lon = get_my_location()
    s = get_station_ids_close_to(lat,lon)
    d = json.dumps(s,indent=2)
    print(d)
    
def test_flam():
  name = "Flamborough Street, Limehouse"
  n = get_num(home[name],term='NbBikes')
  print(name, n)
  
if __name__ == '__main__':
  main()

