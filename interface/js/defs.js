/***
 * Useful definitions
 */
/*age.png              born.svg      Home_Icon.svg  other_family.png  school.svg        spouse.svg        UN_Members_Flags.JPG
age.svg              employee.svg  links          parents.png       shareholders.png  Tombstone.svg
alternate_names.svg  founder.svg   members.jpg    parent.svg        sibling.png       top_employee.jpg
*/

var _RELATIONS = [{
    "name": "per:age",
    "short": "age",
    "image": "age.svg",
    "icon" : "", 
    "template": "{subject} is {object} old.",
    "subject-types": ["PER"],
    "object-types": ["NUM"]
  },{
    "name": "per:alternate_names",
    "short": "alias",
    "image": "alternate_names.svg",
    "icon": "",
    "template": "{subject} is also known as {object}.",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:place_of_birth",
    "short": "born at",
    "image": "born.svg",
    "icon": "",
    "template": "{subject} was born at {object}.",
    "subject-types": ["PER"],
    "object-types": ["GPE"]
  },{
    "name": "per:place_of_residence",
    "short": "lived at",
    "image": "", 
    "icon": "fa-home",
    "template": "{subject} lived at {object}.",
    "subject-types": ["PER"],
    "object-types": ["GPE"]
  },{
    "name": "per:place_of_death",
    "short": "died at",
    "image": "Tombstone.svg",
    "icon": "", 
    "template": "{subject} died at {object}.",
    "subject-types": ["PER"],
    "object-types": ["GPE"]
  },{
    "name": "per:date_of_birth",
    "short": "born on",
    "image": "born.svg",
    "icon": "",
    "template": "{subject} was born on {object}.",
    "subject-types": ["PER"],
    "object-types": ["DATE"]
  },{
    "name": "per:date_of_death",
    "short": "died on",
    "template": "{subject} died on {object}.",
    "image": "Tombstone.svg",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["DATE"]
  },{
    "name": "per:schools_attended",
    "short": "studied at",
    "template": "{subject} studied at {object}.",
    "image": "school.svg",
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["ORG"]
  },{
    "name": "per:employee_or_member_of",
    "short": "works for",
    "image": "employee.svg", 
    "icon": "", 
    "template": "{subject} works for {object}.",
    "subject-types": ["PER"],
    "object-types": ["ORG", "GPE"]
  },{
    "name": "per:parents",
    "short": "child of",
    "template": "{subject} is the child of {object}.",
    "image": "parents.png", 
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:children",
    "short": "parent of",
    "template": "{subject} is the parent of {object}.",
    "image": "parents.png", 
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:spouse",
    "short": "spouse",
    "template": "{subject} is the spouse of {object}.",
    "image": "spouse.svg", 
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:sibling",
    "short": "sibling of",
    "template": "{subject} is the sibling of {object}.",
    "image": "sibling.svg", 
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:other_family",
    "short": "other family",
    "template": "{subject} and {object} are otherwise family.",
    "image": "other_family.png", 
    "icon": "",
    "subject-types": ["PER"],
    "object-types": ["PER"]
  },{
    "name": "per:title",
    "short": "professional title",
    "image": "", 
    "icon": "fa-id-card-o",
    "template": "{subject} is a {object}.",
    "subject-types": ["PER"],
    "object-types": ["TITLE"]
  },{
    "name": "org:alternate_names",
    "short": "alias",
    "image": "alternate_names.svg", 
    "icon": "",
    "template": "{subject} is also known as {object}.",
    "subject-types": ["ORG"],
    "object-types": ["ORG"]
  },{
    "name": "org:place_of_headquarters",
    "short": "headquartered at",
    "template": "{subject} is headquartered at {object}.",
    "image": "", 
    "icon": "fa-building-o",
    "subject-types": ["ORG"],
    "object-types": ["GPE"]
  },{
    "name": "org:date_founded",
    "short": "founded on",
    "template": "{subject} was founded on {object}.",
    "image": "founder.svg", 
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["DATE"]
  },{
    "name": "org:date_dissolved",
    "short": "closed/dissolved on",
    "template": "{subject} was closed/dissolved on {object}.",
    "image": "", 
    "icon": "fa-trash-o",
    "subject-types": ["ORG"],
    "object-types": ["DATE"]
  },{
    "name": "org:founded_by",
    "short": "founded by",
    "template": "{subject} was founded by {object}.",
    "image": "founder.svg", 
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["PER", "ORG", "GPE"]
  },{
    "name": "org:member_of",
    "short": "member of",
    "template": "{subject} is a member of {object}.",
    "image": "members.jpg", 
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["ORG"]
  },{
    "name": "org:members",
    "short": "has member",
    "template": "{subject} has {object} as a member.",
    "image": "members.jpg", 
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["ORG"]
  },{
    "name": "org:number_of_employees_members",
    "short": "number of employees or members",
    "template": "{subject} has {object} members or employees.",
    "image": "employee.svg",
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["NUM"]
  },{
    "name": "org:subsidiaries",
    "short": "owns",
    "template": "{subject} owns {object}.",
    "image": "", 
    "icon": "fa-sitemap",
    "subject-types": ["ORG"],
    "object-types": ["ORG"]
  },{
    "name": "org:parents",
    "short": "owned by",
    "template": "{subject} is owned by {object}.",
    "image": "", 
    "icon": "fa-sitemap",
    "subject-types": ["ORG"],
    "object-types": ["ORG"]
  },{
    "name": "org:shareholders",
    "short": "shareholder",
    "template": "{object} is a shareholder of {subject}.",
    "image": "shareholders.png", 
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["PER", "ORG"]
  },{
    "name": "org:holds_shares_in",
    "short": "holds shares in",
    "template": "{subject} holds shares in {object}.",
    "image": "shareholders.png", 
    "icon": "",
    "subject-types": ["ORG"],
    "object-types": ["ORG"]
  },{
    "name": "gpe:member_of",
    "short": "member_of",
    "template": "{subject} is a member of {object}.",
    "image": "members.jpg", 
    "icon": "",
    "subject-types": ["GPE"],
    "object-types": ["ORG"]
  },{
    "name": "gpe:subsidiaries",
    "short": "owns",
    "template": "{subject} owns {object}.",
    "image": "", 
    "icon": "fa-sitemap",
    "subject-types": ["GPE"],
    "object-types": ["ORG"]
  },{
    "name": "no_relation",
    "short": "unrelated",
    "template": "{subject} and {object} are otherwise related or not related.",
    "image" : "", 
    "icon": "fa-times",
    "subject-types": ["PER", "ORG", "GPE"],
    "object-types": ["PER", "ORG", "GPE", "DATE", "NUM", "TITLE"]
  }];

var RelationLabel = function(r) {
  this.name = r.name;
  this.short = r.short;
  this.icon = r.icon;
  this.image = r.image;
  this.template = r.template;
  this.subjectTypes = r["subject-types"];
  this.objectTypes = r["object-types"];
}

RelationLabel.prototype.renderTemplate = function(mentionPair) {
  var subject = (mentionPair[0].entity) ? mentionPair[0].entity.gloss : mentionPair[0].gloss;
  var object = (mentionPair[1].entity) ? mentionPair[1].entity.gloss : mentionPair[1].gloss;
  return this.template
    .replace("{subject}", "<span class='subject'>" + subject + "</span>")
    .replace("{object}", "<span class='object'>" + object + "</span>");
}

RelationLabel.prototype.isApplicable = function(mentionPair) {
  return this.subjectTypes.indexOf(mentionPair[0].type.name) >= 0 
          && this.objectTypes.indexOf(mentionPair[1].type.name) >= 0;
}


var RELATIONS = [];
_RELATIONS.forEach(function(r) {RELATIONS.push(new RelationLabel(r))});

var _TYPES = [{
  "idx": 0,
  "name": "PER",
  "gloss": "Person",
  "icon": "fa-user",
  "linking": "wiki-search",
 },{
  "idx": 1,
  "name": "ORG",
  "gloss": "Organization",
  "icon": "fa-building",
  "linking": "wiki-search",
 },{
  "idx": 2,
  "name": "GPE",
  "gloss": "City/State/Country",
  "icon": "fa-globe",
  "linking": "wiki-search",
 },{
  "idx": 3,
  "name": "DATE",
  "gloss": "Date",
  "icon": "fa-calendar",
  "linking": "date-picker",
 },{
  "idx": 4,
  "name": "TITLE",
  "gloss": "Title",
  "icon": "fa-id-card-o",
  "linking": "",
 }];
var EntityType = function(t) {
  this.name = t.name;
  this.gloss = t.gloss;
  this.icon = t.icon;
}
var TYPES = {};
_TYPES.forEach(function(t) {TYPES[t.name] = t});


// 
var Mention = function(m) {
  this.id = Mention.count++;
  this.tokens = m.tokens;
  this.sentenceIdx = m.tokens[0].sentenceIdx;
  this.type = m.type && TYPES[m.type];
  this.gloss = m.gloss;

  this.entity = m.entity;
}
Mention.count = 0;
Mention.fromTokens = function(tokens) {
  return new Mention({
    "tokens": tokens,
    "sentenceIdx": tokens[0].token.sentenceIdx,
    "type": undefined,
    "gloss": Mention.textFromTokens(tokens)
  });
}
Mention.textFromTokens = function(tokens) {
  text = "";
  for (i = 0; i < tokens.length; i++){
    text += tokens[i].textContent;
  }
  console.log(text);
  return text.replace("&nbsp;", " ");
}

// Returns the text represented within the spans of text. 
Mention.prototype.text = function(){
  return Mention.textFromTokens(this.tokens);
}

// Compute levenshtein distance from input @string
Mention.prototype.levenshtein = function(string){
  return window.Levenshtein.get(this.text(), string);
}

// Creates a new entity from a @canonical_mention and @type.
function Entity(canonicalMention) {
  console.log(canonicalMention);
  this.idx = 1 + Entity.count++;
  this.id = "e-" + this.idx;
  this.gloss = canonicalMention.gloss;
  this.type = canonicalMention.type;
  this.mentions = [];

  this.addMention(canonicalMention);
}
Entity.count = 0;
Entity.map = {};

Entity.prototype.addMention = function(mention) {
  console.log("Adding mention", mention, this);
  // Set the type of the mention if it hasn't already been set.
  if (mention.type === null) {
    mention.type = this.type;
  }
  mention.entity = this;

  this.mentions = [mention];
  Entity.map[mention.id] = this;
}

// Returns "true" if the mention has > 0 mentions.
Entity.prototype.removeMention = function(mention) {
  console.log(mention, this.mentions);
  var index = this.mentions.indexOf(mention);
  console.assert(index > -1);
  if (index > -1) {
    this.mentions.splice(index, 1);
  }
  delete Entity.map[mention.id];

  return (this.mentions.length > 0);
};

// returns the minimum levenshtein distance from all the mentions in the
// entity.
Entity.prototype.levenshtein = function(mentionText) {
  var bestMatch = null
  var bestScore = 1000;
  for (var i = 0; i < this.mentions.length; i++) {
    var score = this.mentions[i].levenshtein(mentionText);
    if (bestScore > score) {
      bestScore = score;
      bestMatch = this.mentions[i]
    }
  }
  return bestScore;
}
