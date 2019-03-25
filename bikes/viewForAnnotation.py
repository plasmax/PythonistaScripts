from objc_util import *
import ui
import ctypes
import weakref
import sys

py3 = (sys.version_info.major == 3)
_map_delegate_cache = weakref.WeakValueDictionary()

try:
	# If the script was run before, the class already exists.
	OMMapViewDelegate = ObjCClass(
		'OMMapViewDelegate'
	)
except:
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
	IMPTYPE2 = ctypes.CFUNCTYPE(
		None, c_void_p, 
		c_void_p, c_void_p, c_void_p
	)
	def mapView_viewForAnnotation_imp(
			self, cmd, mk_mapview, annotation
		):
		identifier = 'BikeMarker'
		#if annotation.isKind(
			#MKUserLocation.self):
			#return None
		annotationView = None
		'''
		# Resolve weak reference from delegate to mapview:
		map_view = _map_delegate_cache[
			self
		].map_view_ref()
		if map_view:
			annotationView = map_view.dequeueReusableAnnotationView(
				identifier
			)
		'''
		if not annotationView:
			annotationView = ObjCClass(
				'MKMarkerAnnotationView'
			).alloc(
			).initWithAnnotation_reuseIdentifier_(
				annotation, identifier
			)
		annotationView.glyphText = '    '
		annotationView.markerTintColor = UIColor.blue
		return annotationView
		
	imp2 = IMPTYPE2(
		mapView_viewForAnnotation_imp
	)
	# This is a little ugly, but we need to make sure that `imp` isn't garbage-collected:
	ui._retain_me_mapview_delegate_imp1 = imp2
	sel2 = sel(
		b'mapView:viewForAnnotation:'
		if py3 else 
		'mapView:viewForAnnotation:'
	)
	c.class_addMethod(
		class_ptr, 
		sel2, 
		imp2, 
		(
			b'v0@0:0@0B0' 
			if py3 else 
			'v0@0:0@0B0'
		)
	)
	
	# -- end of max stuff --
	c.objc_registerClassPair(class_ptr)
	OMMapViewDelegate = ObjCClass(
		b'OMMapViewDelegate'
		if py3 else
		'OMMapViewDelegate'
	)

sel2 = sel(
		b'mapView:viewForAnnotation:'
		if py3 else 
		'mapView:viewForAnnotation:'
)
print(sel2)
sm = c.class_getInstanceMethod(
	OMMapViewDelegate,#.superclass(),
	sel2,#':viewForAnnotation:'
)
print(sm)
