#!/usr/bin/python3

import json
from pprint import pprint
import pystache
import uuid
import collections
import webcolors
import sys

class ViewConstraint():
	def __init__(self, item1=None, item2=None, attribute1="", attribute2="", constant=0, multiplier=1):
		self.item1 = item1;
		self.item2 = item2;
		self.attribute1 = attribute1[0].lower() + attribute1[1:];
		self.attribute2 = attribute2[0].lower() + attribute2[1:];
		self.constant = constant;
		self.multiplier = multiplier;
		self.id = uuid.uuid4()

	@property
	def attribute(self):
		return self.attribute1;

	@property
	def item(self):
		return self.item1;

	@property
	def inner(self):
		return self.item2==self.item1 and self.attribute1==self.attribute2;

class View():
	superview = None
	views = []

	def __init__(self, viewname="", viewtype=""):
		viewtype_components = viewtype.split(':')
		viewclass = None
		if len(viewtype_components) > 1:
			viewclass = viewtype_components[1]
		viewtype = viewtype_components[0]
		self.type = viewtype[2].lower() + viewtype[3:] if viewtype != None and len(viewtype) > 0 else None;
		self.name = viewname;
		self.id = uuid.uuid4()
		self.constraints = []
		self.classname = viewclass
		self.attributes = {}
		self.subviews = []
		self.superview = View.superview

	@property
	def color_attributes(self):
		result = []
		for key, value in self.attributes.items():
			if "color" in key.lower():
				colorAttr = {}
				colorAttr["key"] = key[0].lower() + key[1:]
				rgbTuple = webcolors.name_to_rgb(value) if value[0] != '#' else webcolors.hex_to_rgb(value)
				colorAttr["red"] = rgbTuple[0]/255
				colorAttr["green"] = rgbTuple[1]/255
				colorAttr["blue"] = rgbTuple[2]/255
				result.append(colorAttr)
		return result

	@property
	def image_attribute(self):
		result = None
		for key, value in self.attributes.items():
			if "image" == key.lower():
				result = value
		return result

	@property
	def font_attributes(self):
		result = []
		for key, value in self.attributes.items():
			if "font" in key.lower():
				fontAttr = {}
				fontAttr["key"] = key[0].lower() + key[1:]
				fontAttrComponents = value.split(':')
				fontAttr["name"] = fontAttrComponents[0]
				fontAttr["family"] = fontAttrComponents[1]
				fontAttr["points"] = fontAttrComponents[2]
				result.append(fontAttr)
		return result

	@property
	def text(self):
		result = None
		for key, value in self.attributes.items():
			if "text" == key.lower():
				result = value
		return result
	

	@property
	def opaque(self):
	    return "YES" if self.type != "label" else "NO"

	@staticmethod
	def build_views(viewnames, last_iteration=-1):
		if len(viewnames) == 0:
			return
		to_be_processed = {}
		for key, value in viewnames.items():
			viewname_components = key.split(':')
			viewname = viewname_components[0]
			view = View(viewname, value)
			if len(viewname_components) > 1:
				superviewname = viewname_components[1]
				superview = View.by_name(superviewname)
				if superview != None:
					view.superview = superview
					superview.subviews.insert(0, view)
				else:
					to_be_processed[key] = value
			else:
				View.superview.subviews.insert(0, view)
		if len(to_be_processed) == last_iteration:
			sys.stderr.write("Wrong superview!\n")
			sys.exit()
		else:
			View.build_views(to_be_processed, len(to_be_processed))

	def by_name_of_subview(self, name):
		for value in self.subviews:
			if value.name == name:
				return value
			elif len(value.subviews) > 0:
				result = value.by_name_of_subview(viewname)
				if result != None:
					return result
		return None

	@classmethod
	def by_name(cls, name, current_view=None):
		if name == "superview":
			return current_view.superview;
		return View.superview.by_name_of_subview(name)

with open(sys.argv[1]) as data_file:
	try:    
		data = json.load(data_file)
	except ValueError:
		sys.stderr.write("Invalid JSON!\n")
		sys.exit()

View.superview = View()
view_names = data["views"]
View.build_views(view_names)

with open('xib.mustache') as data_file:    
    template = data_file.read()

with open('recursive_partial.mustache') as data_file:    
    partial = data_file.read()

def constraint_from_view(view, constraint_data_parsed, last_view=None):
	constant = 0
	multiplier = 1
	if constraint_data_parsed[-1][-1] == 'x':
		multiplier = constraint_data_parsed[-1][:-1]
	else:
		constant = constraint_data_parsed[-1]
	if len(constraint_data_parsed) == 2:
		result = ViewConstraint(item1=view, 
						attribute1=constraint_data_parsed[0],  
						item2=view, 
						attribute2=constraint_data_parsed[0],
						constant=constant,
						multiplier=multiplier)
	elif len(constraint_data_parsed) == 3:
		if last_view == None:
			result = None
		else:
			result = ViewConstraint(item1=last_view, 
							attribute1=constraint_data_parsed[0],  
							item2=view, 
							attribute2=constraint_data_parsed[1],
							constant=constant,
							multiplier=multiplier)
	else:
		result = ViewConstraint(item1=view, 
						attribute1=constraint_data_parsed[0], 
						item2=View.by_name(constraint_data_parsed[1], view), 
						attribute2=constraint_data_parsed[2], 
						constant=constant,
						multiplier=multiplier)
	return result

def add_constraints_from_name(viewname, constraint_data_parsed, last_view=None):
	view = View.by_name(viewname)
	constraint = constraint_from_view(view, constraint_data_parsed, last_view)
	if constraint != None:
		if not constraint.inner:
			view.superview.constraints.append(constraint)
		else:
			view.constraints.append(constraint)

constraints_unparsed = data["constraints"]

for constraint_data in constraints_unparsed:
	constraint_data_parsed = constraint_data[1].split(':')
	if isinstance(constraint_data[0], list):
		last_view = None
		for viewname in constraint_data[0]:
			add_constraints_from_name(viewname, constraint_data_parsed, last_view)
			last_view = View.by_name(viewname)
	else:
		viewname = constraint_data[0]
		add_constraints_from_name(viewname, constraint_data_parsed)

attributes_unparsed = data["attributes"]
for attribute in attributes_unparsed:
	if isinstance(attribute[0], list):
		for viewname in attribute[0]:
			view = View.by_name(viewname)
			attribute_components = attribute[1].split(':', 1)
			view.attributes[attribute_components[0]] = attribute_components[1]
	else:	
		viewname = attribute[0]
		view = View.by_name(viewname)
		attribute_components = attribute[1].split(':', 1)
		view.attributes[attribute_components[0]] = attribute_components[1]

print(pystache.render(template, {'views': View.superview.subviews, 'superview': View.superview, "recursive_partial":partial}))