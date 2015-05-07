#!/usr/bin/python3

import json
from pprint import pprint
import pystache
import uuid
import collections
import webcolors
import sys

class ViewConstraint():
	def __init__(self, item1=None, item2=None, attribute1="", attribute2="", constant=None):
		self.item1 = item1;
		self.item2 = item2;
		self.attribute1 = attribute1.lower();
		self.attribute2 = attribute2.lower();
		self.constant = constant;
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
		self.inner_constraints = []
		self.classname = viewclass
		self.attributes = {}

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
		if self.type == "imageView":
			for key, value in self.attributes.items():
				if "image" == key.lower():
					result = value
		return result

	@staticmethod
	def build_views(viewnames):
		result = []
		for key, value in viewnames.items():
			view = View(key, value)
			result.append(view)
		return result

	@classmethod
	def by_name(cls, name):
		views=cls.views
		if name == "superview":
			return cls.superview;
		for value in views:
			if value.name == name:
				return value
		return None

with open(sys.argv[1]) as data_file:
	try:    
		data = json.load(data_file)
	except ValueError:
		sys.stderr.write("Invalid JSON!\n")
		sys.exit()

View.superview = View()
view_names = data["views"]
View.views = View.build_views(view_names)

with open('xib.mustache') as data_file:    
    template = data_file.read()

def constraint_from_view(view, constraint_data_parsed, last_view=None):
	if len(constraint_data_parsed) == 2:
		result = ViewConstraint(item1=view, 
						attribute1=constraint_data_parsed[0],  
						item2=view, 
						attribute2=constraint_data_parsed[0],
						constant=constraint_data_parsed[-1])
	elif len(constraint_data_parsed) == 3:
		if last_view == None:
			result = None
		else:
			result = ViewConstraint(item1=last_view, 
							attribute1=constraint_data_parsed[0],  
							item2=view, 
							attribute2=constraint_data_parsed[1],
							constant=constraint_data_parsed[-1])
	else:
		result = ViewConstraint(item1=view, 
						attribute1=constraint_data_parsed[0], 
						item2=View.by_name(constraint_data_parsed[1]), 
						attribute2=constraint_data_parsed[2], 
						constant=constraint_data_parsed[-1])
	return result

def add_constraints_from_name(viewname, constraint_data_parsed, constraints, last_view=None):
	view = View.by_name(viewname)
	constraint = constraint_from_view(view, constraint_data_parsed, last_view)
	if constraint != None:
		if not constraint.inner:
			constraints.append(constraint)
		else:
			view.inner_constraints.append(constraint)

constraints_unparsed = data["constraints"]
constraints = []

for constraint_data in constraints_unparsed:
	constraint_data_parsed = constraint_data[1].split(':')
	if isinstance(constraint_data[0], list):
		last_view = None
		for viewname in constraint_data[0]:
			add_constraints_from_name(viewname, constraint_data_parsed, constraints, last_view)
			last_view = View.by_name(viewname)
	else:	
		add_constraints_from_name(viewname, constraint_data_parsed, constraints)

attributes_unparsed = data["attributes"]
for attribute in attributes_unparsed:
	if isinstance(attribute[0], list):
		for viewname in attribute[0]:
			view = View.by_name(viewname)
			attribute_components = attribute[1].split(':')
			view.attributes[attribute_components[0]] = attribute_components[1]
	else:	
		viewname = attribute[0]
		view = View.by_name(viewname)
		attribute_components = attribute[1].split(':')
		view.attributes[attribute_components[0]] = attribute_components[1]

print(pystache.render(template, {'views': View.views, 'superview': View.superview, "constraints": constraints}))