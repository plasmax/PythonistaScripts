# coding: utf-8
'''
NOTE: This requires the latest beta of Pythonista 1.6 (build 160022)
Demo of a custom ui.View subclass that embeds a native map view using MapKit (via objc_util). Tap and hold the map to drop a pin.
The MapView class is designed to be reusable, but it doesn't implement *everything* you might need. I hope that the existing methods give you a basic idea of how to add new capabilities though. For reference, here's Apple's documentation about the underlying MKMapView class: http://developer.apple.com/library/ios/documentation/MapKit/reference/MKMapView_Class/index.html
If you make any changes to the OMMapViewDelegate class, you need to restart the app. Because this requires creating a new Objective-C class, the code can basically only run once per session (it's not safe to delete an Objective-C class at runtime as long as instances of the class potentially exist).
'''

from objc_util import *
import ctypes
import ui
import location
import time
import weakref
import sys
import bikes

py3 = sys.version_info.major == 3

# _map_delegate_cache is used to get a reference to the MapView from the (Objective-C) delegate callback. The keys are memory addresses of `OMMapViewDelegate` (Obj-C) objects, the values are `ObjCInstance` (Python) objects. This mapping is necessary because `ObjCInstance` doesn't guarantee that you get the same object every time when you instantiate it with a pointer (this may change in future betas). MapView stores a weak reference to itself in the specific `ObjCInstance` that it creates for its delegate.
_map_delegate_cache = weakref.WeakValueDictionary()

# Create a new Objective-C class to act as the MKMapView's delegate...
try:
	# If the script was run before, the class already exists.
	OMMapViewDelegate = ObjCClass('OMMapViewDelegate')
except:
	IMPTYPE = ctypes.CFUNCTYPE(None, c_void_p, c_void_p, c_void_p, c_bool)
	def mapView_regionDidChangeAnimated_imp(self, cmd, mk_mapview, animated):
		# Resolve weak reference from delegate to mapview:
		map_view = _map_delegate_cache[self].map_view_ref()
		if map_view:
			map_view._notify_region_changed()
	imp = IMPTYPE(mapView_regionDidChangeAnimated_imp)
	# This is a little ugly, but we need to make sure that `imp` isn't garbage-collected:
	ui._retain_me_mapview_delegate_imp1 = imp
	NSObject = ObjCClass(
		b'NSObject' if py3 else 'NSObject'
	)
	class_ptr = c.objc_allocateClassPair(
		NSObject.ptr, 
		(
			b'OMMapViewDelegate'
			if py3 else 'OMMapViewDelegate'
		), 
		0
	)
	selector = sel(
		b'mapView:regionDidChangeAnimated:'
		if py3 else 
		'mapView:regionDidChangeAnimated:'
	)
	c.class_addMethod(
		class_ptr, 
		selector, 
		imp, 
		(
			b'v0@0:0@0B0' 
			if py3 else 
			'v0@0:0@0B0'
		)
	)
	c.objc_registerClassPair(class_ptr)
	OMMapViewDelegate = ObjCClass(
		b'OMMapViewDelegate'
		if py3 else
		'OMMapViewDelegate'
	)

class CLLocationCoordinate2D (Structure):
	_fields_ = [
		('latitude', c_double), 
		('longitude', c_double)
	]
class MKCoordinateSpan (Structure):
	_fields_ = [
		('d_lat', c_double), 
		('d_lon', c_double)
	]
class MKCoordinateRegion (Structure):
	_fields_ = [
		('center', CLLocationCoordinate2D), 
		('span', MKCoordinateSpan)
	]

class MapView (ui.View):
	@on_main_thread
	def __init__(self, *args, **kwargs):
		ui.View.__init__(self, *args, **kwargs)
		MKMapView = ObjCClass('MKMapView')
		frame = CGRect(
			CGPoint(0, 0), 
			CGSize(self.width, self.height)
		)
		self.mk_map_view = MKMapView.alloc(
		).initWithFrame_(frame)
		flex_width, flex_height = (1<<1), (1<<4)
		self.mk_map_view.setAutoresizingMask_(
			flex_width|flex_height
		)
		self_objc = ObjCInstance(self)
		self_objc.addSubview_(self.mk_map_view)
		self.mk_map_view.release()
		self.long_press_action = None
		self.scroll_action = None
		#NOTE: The button is only used as a convenient action target for the gesture recognizer. While this isn't documented, the underlying UIButton object has an `-invokeAction:` method that takes care of calling the associated Python action.
		self.gesture_recognizer_target = ui.Button()
		self.gesture_recognizer_target.action = self.long_press
		UILongPressGestureRecognizer = ObjCClass(
			'UILongPressGestureRecognizer'
		)
		self.recognizer = UILongPressGestureRecognizer.alloc(
		).initWithTarget_action_(
			self.gesture_recognizer_target, sel('invokeAction:')
		).autorelease()
		self.mk_map_view.addGestureRecognizer_(
			self.recognizer
		)
		self.long_press_location = ui.Point(0, 0)
		self.map_delegate = OMMapViewDelegate.alloc(
		).init().autorelease()
		self.mk_map_view.setDelegate_(
			self.map_delegate
		)
		self.map_delegate.map_view_ref = weakref.ref(self)
		_map_delegate_cache[
			self.map_delegate.ptr
		] = self.map_delegate

	def long_press(self, sender):
		#NOTE: The `sender` argument will always be the dummy ui.Button that's used as the gesture recognizer's target, just ignore it...
		gesture_state = self.recognizer.state()
		if gesture_state == 1 and callable(self.long_press_action):
			loc = self.recognizer.locationInView_(self.mk_map_view)
			self.long_press_location = ui.Point(loc.x, loc.y)
			self.long_press_action(self)
		
	@on_main_thread
	def add_pin(self, lat, lon, title, subtitle=None, select=False):
		'''Add a pin annotation to the map'''
		MKPointAnnotation = ObjCClass(
			'MKPointAnnotation'
		)
		coord = CLLocationCoordinate2D(lat, lon)
		annotation = MKPointAnnotation.alloc(
		).init().autorelease()
		annotation.setTitle_(title)
		if subtitle:
			annotation.setSubtitle_(subtitle)
		annotation.setCoordinate_(
			coord, 
			restype=None, argtypes=[CLLocationCoordinate2D]
		)
		self.mk_map_view.addAnnotation_(
			annotation
		)
		if select:
			(
				self.mk_map_view
			).selectAnnotation_animated_(
				annotation, True
			)

	@on_main_thread
	def remove_all_pins(self):
		'''Remove all annotations (pins) from the map'''
		self.mk_map_view.removeAnnotations_(
			self.mk_map_view.annotations()
		)

	@on_main_thread
	def set_region(self, lat, lon, d_lat, d_lon, animated=False):
		'''Set latitude/longitude of the view's center and the zoom level (specified implicitly as a latitude/longitude delta)'''
		region = MKCoordinateRegion(
			CLLocationCoordinate2D(lat, lon),
			MKCoordinateSpan(d_lat, d_lon)
		)
		self.mk_map_view.setRegion_animated_(
			region, animated, restype=None, argtypes=[MKCoordinateRegion, c_bool]
		)

	@on_main_thread
	def set_center_coordinate(self, lat, lon, animated=False):
		'''Set latitude/longitude without changing the zoom level'''
		coordinate = CLLocationCoordinate2D(lat, lon)
		self.mk_map_view.setCenterCoordinate_animated_(coordinate, animated, restype=None, argtypes=[CLLocationCoordinate2D, c_bool])

	@on_main_thread
	def get_center_coordinate(self):
		'''Return the current center coordinate as a (latitude, longitude) tuple'''
		coordinate = self.mk_map_view.centerCoordinate(
			restype=CLLocationCoordinate2D, argtypes=[]
		)
		return coordinate.latitude, coordinate.longitude

	@on_main_thread
	def point_to_coordinate(self, point):
		'''Convert from a point in the view (e.g. touch location) to a latitude/longitude'''
		coordinate = (
			self.mk_map_view
		).convertPoint_toCoordinateFromView(
			CGPoint(*point), 
			self._objc_ptr, restype=CLLocationCoordinate2D, 
			argtypes=[CGPoint, c_void_p]
		)
		return coordinate.latitude, coordinate.longitude

	def _notify_region_changed(self):
		if callable(self.scroll_action):
			self.scroll_action(self)


# --------------------------------------
# DEMO:

def long_press_action(sender):
	# Add a pin when the MapView recognizes a long-press
	c = sender.point_to_coordinate(
		sender.long_press_location
	)
	sender.remove_all_pins()
	sender.add_pin(c[0], c[1], 'Dropped Pin', str(c), select=True)
	sender.set_center_coordinate(c[0], c[1], animated=True)

def scroll_action(sender):
	# Show the current center coordinate in the title bar after the map is scrolled/zoomed:
	sender.name = 'lat/long: %.2f, %.2f' % sender.get_center_coordinate()

home_stations = {
  "Flamborough Street, Limehouse": {
    "id": "BikePoints_480",
    "lat": 51.512871,
    "lon": -0.038986
  },
  "Westferry DLR, Limehouse": {
    "id": "BikePoints_510",
    "lat": 51.509303,
    "lon": -0.025996
  },
  "Salmon Lane, Limehouse": {
    "id": "BikePoints_542",
    "lat": 51.514115,
    "lon": -0.033828
  },
}

work_stations = {
  "Bouverie Street, Temple": {
    "id": "BikePoints_27",
    "lat": 51.513821,
    "lon": -0.107927
  },
  "Holborn Circus, Holborn": {
    "id": "BikePoints_66",
    "lat": 51.51795,
    "lon": -0.108657
  },
  "Hatton Garden, Holborn": {
    "id": "BikePoints_67",
    "lat": 51.518825,
    "lon": -0.108028
  },
  "Arundel Street, Temple": {
    "id": "BikePoints_79",
    "lat": 51.511726,
    "lon": -0.113855
  },
  "Chancery Lane, Holborn": {
    "id": "BikePoints_82",
    "lat": 51.514274,
    "lon": -0.111257
  },
  "Breams Buildings, Holborn": {
    "id": "BikePoints_84",
    "lat": 51.515937,
    "lon": -0.111778
  },
  "Strand, Strand": {
    "id": "BikePoints_174",
    "lat": 51.512529,
    "lon": -0.115163
  },
  "Carey Street, Holborn": {
    "id": "BikePoints_232",
    "lat": 51.51501,
    "lon": -0.112753
  },
  "New Fetter Lane, Holborn": {
    "id": "BikePoints_546",
    "lat": 51.517428,
    "lon": -0.107987
  }
}
	


def main():
	# Optimization: Don't create a new view if the widget already shows the calculator.
	widget_name = __file__ + str(os.stat(__file__).st_mtime)
	widget_view = appex.get_widget_view()
	if widget_view is None or widget_view.name != widget_name:
		widget_view = BikeView()
		widget_view.name = widget_name
		appex.set_widget_view(widget_view)
		
home_loc = {
	'lat': 51.509980,
	'lon': -0.030770
}
home_ll = (51.509980,-0.030770)

def main():
	# Create and present a MapView:
	v = MapView(frame=(0, 0, 500, 500))
	v.long_press_action = long_press_action
	v.scroll_action = scroll_action
	v.present('sheet')
	# Add a pin with the current location (if available), and zoom to that location:
	import location
	location.start_updates()
	time.sleep(1)
	loc = location.get_location()
	location.stop_updates()
	if loc:
		lat, lon = loc['latitude'], loc['longitude']
		#lat,lon=home_ll
		v.set_region(
			lat, lon, 0.05, 0.05, animated=False
		)
		v.add_pin(
			lat, 
			lon, 
			'Current Location', 
			str((lat, lon)),
			#select=True
		)
		#lon=-2
		if lon>-0.07:
			stations=home_stations
		else:
			stations=work_stations
		#bikes.get_close_stations()
		for name,d in stations.items():

			response = bikes.get_bikes_and_spaces(
				d['id']
			)
			if response is None:
				continue
			b,s = response
			
			v.add_pin(
				d['lat'],
				d['lon'],
				'%s/%s'%(b,b+s),
				name
				#str((d['lat'],d['lon']))
			)
	#import appex #py3
	#appex.set_widget_view(v)
	
if __name__ == '__main__':
	main()
