/***
 * Useful definitions
 */

var RELATIONS = [{
    "name": "per:age",
    "short": "age",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["NUM"]
  },{
    "name": "per:alternate_names",
    "short": "alias",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:place_of_birth",
    "short": "born at",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["GPE"]
  },{
    "name": "per:place_of_residence",
    "short": "lived at",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["GPE"]
  },{
    "name": "per:place_of_death",
    "short": "died at",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["GPE"]
  },{
    "name": "per:date_of_birth",
    "short": "born on",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["DATE"]
  },{
    "name": "per:date_of_death",
    "short": "died on",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["DATE"]
  },{
    "name": "per:schools_attended",
    "short": "studied at",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["ORG"]
  },{
    "name": "per:employee_or_member_of",
    "short": "works at",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["ORG", "GPE"]
  },{
    "name": "per:children",
    "short": "parent of",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:spouse",
    "short": "spouse",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:sibling",
    "short": "sibling of",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:other_family",
    "short": "otherwise related to",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:title",
    "short": "professional title",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["TITLE"]
  },{
    "name": "org:alternate_names",
    "short": "alias",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["ORG"]
  },{
    "name": "org:place_of_headquarters",
    "short": "headquartered at",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["GPE"]
  },{
    "name": "org:date_founded",
    "short": "founded on",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["DATE"]
  },{
    "name": "org:date_dissolved",
    "short": "closed/dissolved on",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["DATE"]
  },{
    "name": "org:founded_By",
    "short": "founded by",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["PER", "ORG", "GPE"]
  },{
    "name": "org:member_of",
    "short": "member of",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["ORG"]
  },{
    "name": "org:number_of_employees_members",
    "short": "number of employees or members",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["NUM"]
  },{
    "name": "org:subsidiaries",
    "short": "owns",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["ORG"]
  },{
    "name": "org:shareholders",
    "short": "shareholders",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["PER", "ORG"]
  },{
    "name": "gpe:member_of",
    "short": "member_of",
    "icon": "",
    "subject-types": ["GPE"],
    "object-types": ["ORG"]
  },{
    "name": "gpe:subsidiaries",
    "short": "owns",
    "icon": "",
    "subject-types": ["GPE"],
    "object-types": ["ORG"]
  }];

