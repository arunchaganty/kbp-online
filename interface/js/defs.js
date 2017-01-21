/***
 * Useful definitions
 */

var _RELATIONS = [{
    "name": "per:age",
    "short": "age",
    "icon": "",
    "template": "{subject} is {object} old.",
    "subject-types": ["PER"],
    "object-types": ["NUM"]
  },{
    "name": "per:alternate_names",
    "short": "alias",
    "icon": "",
    "template": "{subject} is also known as {object}.",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:place_of_birth",
    "short": "born at",
    "icon": "",
    "template": "{subject} was born at {object}.",
    "subject-types": ["PER"],
    "object-types": ["GPE"]
  },{
    "name": "per:place_of_residence",
    "short": "lived at",
    "icon": "",
    "template": "{subject} lived at {object}.",
    "subject-types": ["PER"],
    "object-types": ["GPE"]
  },{
    "name": "per:place_of_death",
    "short": "died at",
    "icon": "",
    "template": "{subject} died at {object}.",
    "subject-types": ["PER"],
    "object-types": ["GPE"]
  },{
    "name": "per:date_of_birth",
    "short": "born on",
    "icon": "",
    "template": "{subject} was born on {object}.",
    "subject-types": ["PER"],
    "object-types": ["DATE"]
  },{
    "name": "per:date_of_death",
    "short": "died on",
    "template": "{subject} died on {object}.",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["DATE"]
  },{
    "name": "per:schools_attended",
    "short": "studied at",
    "template": "{subject} studied at {object}.",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["ORG"]
  },{
    "name": "per:employee_or_member_of",
    "short": "works for",
    "icon": "",
    "template": "{subject} works for {object}.",
    "subject-types": ["PER"],
    "object-types": ["ORG", "GPE"]
  },{
    "name": "per:parents",
    "short": "child of",
    "template": "{subject} is the child of {object}.",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:children",
    "short": "parent of",
    "template": "{subject} is the parent of {object}.",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:spouse",
    "short": "spouse",
    "template": "{subject} is the spouse of {object}.",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:sibling",
    "short": "sibling of",
    "template": "{subject} is the sibling of {object}.",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:other_family",
    "short": "otherwise related to",
    "template": "{subject} is otherwise related to {object}.",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:title",
    "short": "professional title",
    "icon": "",
    "template": "{subject} is a {object}.",
    "subject-types": ["PER"],
    "object-types": ["TITLE"]
  },{
    "name": "org:alternate_names",
    "short": "alias",
    "icon": "",
    "template": "{subject} is also known as {object}.",
    "subject-types": ["ORG"],
    "object-types": ["ORG"]
  },{
    "name": "org:place_of_headquarters",
    "short": "headquartered at",
    "template": "{subject} is headquartered at {object}.",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["GPE"]
  },{
    "name": "org:date_founded",
    "short": "founded on",
    "template": "{subject} was founded on {object}.",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["DATE"]
  },{
    "name": "org:date_dissolved",
    "short": "closed/dissolved on",
    "template": "{subject} was closed/dissolved on {object}.",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["DATE"]
  },{
    "name": "org:founded_by",
    "short": "founded by",
    "template": "{subject} was founded by {object}.",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["PER", "ORG", "GPE"]
  },{
    "name": "org:member_of",
    "short": "member of",
    "template": "{subject} is a member of {object}.",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["ORG"]
  },{
    "name": "org:number_of_employees_members",
    "short": "number of employees or members",
    "template": "{subject} has {object} members or employees.",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["NUM"]
  },{
    "name": "org:subsidiaries",
    "short": "owns",
    "template": "{subject} owns {object}.",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["ORG"]
  },{
    "name": "org:shareholders",
    "short": "shareholders",
    "template": "{object} is a shareholder of {subject}.",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["PER", "ORG"]
  },{
    "name": "gpe:member_of",
    "short": "member_of",
    "template": "{subject} is a member of {object}.",
    "icon": "",
    "subject-types": ["GPE"],
    "object-types": ["ORG"]
  },{
    "name": "gpe:subsidiaries",
    "short": "owns",
    "template": "{subject} owns {object}.",
    "icon": "",
    "subject-types": ["GPE"],
    "object-types": ["ORG"]
  },{
    "name": "no_relation",
    "short": "unrelated",
    "template": "{subject} and {object} are otherwise related or not related.",
    "icon": "",
    "subject-types": ["PER", "ORG", "GPE"],
    "object-types": ["PER", "ORG", "GPE", "DATE", "NUM", "TITLE"]
  }];

var RelationLabel = function(r) {
  this.name = r.name;
  this.short = r.short;
  this.icon = r.icon;
  this.template = r.template;
  this.subjectTypes = r["subject-types"];
  this.objectTypes = r["object-types"];
}

RelationLabel.prototype.renderTemplate = function(mentionPair) {
  return this.template
    .replace("{subject}", "<span class='subject'>" + mentionPair[0].gloss + "</span>")
    .replace("{object}", "<span class='object'>" + mentionPair[1].gloss + "</span>");
}

RelationLabel.prototype.isApplicable = function(mentionPair) {
  return this.subjectTypes.indexOf(mentionPair[0].type) >= 0 
          && this.objectTypes.indexOf(mentionPair[1].type) >= 0;
}


var RELATIONS = [];
_RELATIONS.forEach(function(r) {RELATIONS.push(new RelationLabel(r))});
