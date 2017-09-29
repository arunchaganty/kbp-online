/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['fast-levenshtein/levenshtein'], function(Levenshtein) {
    String.prototype.replaceAll = function(search, replace) {
        if (replace === undefined) {
            return this.toString();
        }
        return this.split(search).join(replace);
    };

    var _RELATIONS = [
      {
          "name": "no_relation",
          "short": "unrelated",
          "template": "{subject} and {object} are otherwise related or not related.",
          "image" : "", 
          "examples": [
            "{Tony Blair} informed the [British] public on Thursday.",
            "{Binney} as accosted by an [FBI] agent.",
          ],
          "icon": "fa-times",
          "subject-types": ["PER", "ORG", "GPE"],
          "object-types": ["PER", "ORG", "GPE", "DATE", "NUM", "TITLE"]
      },{
      // 
      //     "name": "per:age",
      //     "short": "age",
      //     "image": "age.svg",
      //     "icon" : "fa-clock-o", 
      //     "examples": [],
      //     "template": "{subject} is {object} old.",
      //     "subject-types": ["PER"],
      //     "object-types": ["NUM"]
      // },{
      //    "name": "per:alternate_names",
      //    "short": "alias",
      //    "image": "alternate_names.svg",
      //    "icon": "fa-address-book",
      //    "examples": [
      //      "{Dwayne Johnson}, popularly known as [The Rock], ...",
      //        "{Cardozar} ([Snoop Dog]) announced his new song...",
      //    ],
      //    "template": "{subject} is also known as {object}.",
      //    "subject-types": ["PER"],
      //    "object-types": ["PER"]
      //},{
          "name": "per:place_of_birth",
          "short": "born at",
          "image": "born.svg",
          "icon": "fa-birthday-cake",
          "examples": ["{Julia} is a [Hawaiian] native.",
                       "Julia is NOT born in Hawaii if she is a Hawaiian congresswoman."
                      ],
          "template": "{subject} was born at {object}.",
          "subject-types": ["PER"],
          "object-types": ["GPE"]
      },{
          "name": "per:place_of_residence",
          "short": "lived at",
          "image": "", 
          "icon": "fa-home",
          "template": "{subject} lives/lived at {object}.",
          "examples": ["{Mike} lived in [Hawaii] because he grew up or studied there.",
                       "{Mia} lived in [Hawaii] because she is a Hawaiian senator.",
                       "{Mike} does NOT live in [Hawaii] because he visited for a business trip."
                      ],
          "subject-types": ["PER"],
          "object-types": ["GPE"]
      },{
          "name": "per:place_of_death",
          "short": "died at",
          "image": "Tombstone.svg",
          "icon": "fa-bolt", 
          "examples": [
              "{Mike} was mourned in [Philadelphia] where he died last weekend.",
              "{Mike} did not necessarily die in [Kansas City] if that is where he was laid to rest.",
          ],
          "template": "{subject} died at {object}.",
          "subject-types": ["PER"],
          "object-types": ["GPE"]
      },{
          "name": "per:date_of_birth",
          "short": "born on",
          "image": "born.svg",
          "icon": "fa-birthday-cake",
          "examples": [
              "{Mike} was born on [December 31st, 1975].",
          ],
          "template": "{subject} was born on {object}.",
          "subject-types": ["PER"],
          "object-types": ["DATE"]
      },{
          "name": "per:date_of_death",
          "short": "died on",
          "template": "{subject} died on {object}.",
          "image": "Tombstone.svg",
          "icon": "fa-bolt",
          "examples": [
              "{Mike} was died on [December 31st, 2015].",
          ],
          "subject-types": ["PER"],
          "object-types": ["DATE"]
      },{
          "name": "per:organizations_founded",
          "short": "founded by",
          "template": "{subject} founded {object}.",
          "examples": [
              "{Steve Jobs} founded [Apple Inc.] in 1976.",
              "{Abu al-Zarqawi} is widely regarded to be the founder of [ISIS].",
          ],
          "image": "founder.svg",
          "icon": "fa-building",
          "subject-types": ["PER"],
          "object-types": ["ORG"]
      },{
          "name": "per:holds_shares_in",
          "short": "holds shares in",
          "template": "{subject} holds/held shares in {object}.",
          "image": "shareholders.png", 
          "examples": [
            "{Eric Schmidt} a the leading shareholder in [Google].",
          ],
          "icon": "fa-line-chart",
          "subject-types": ["PER"],
          "object-types": ["ORG"]
      },{
          "name": "per:schools_attended",
          "short": "studied at",
          "template": "{subject} is studying/studied at {object}.",
          "examples": [
            "{Eric Schmidt}, an [UC Berkeley]-graduate ...",
          ],
          "image": "school.svg",
          "icon": "fa-graduation-cap",
          "subject-types": ["PER"],
          "object-types": ["ORG"]
      },{
          "name": "per:employee_or_member_of",
          "short": "works for",
          "image": "employee.svg", 
          "icon": "fa-black-tie", 
          "template": "{subject} works/worked for {object}.",
          "examples": ["{Mike} is for [Shell] if he is Shell's spokesperson.",
                       "{Mia} works for [America] if she is an American ambassador.",
                       "{Mia} does NOT work for the [Fox News] if she was interviewed on Fox News.",
                      ],
          "subject-types": ["PER"],
          "object-types": ["ORG", "GPE"]
      },{
          "name": "per:parents",
          "short": "child of",
          "template": "{subject} is the child of {object}.",
          "examples": [
                       "{Fisher}'s mother, [Debbie Reynolds].",
          ],
          "image": "parents.png", 
          "icon": "fa-child",
          "subject-types": ["PER"],
          "object-types": ["PER"]
      },{
          "name": "per:children",
          "short": "parent of",
          "template": "{subject} is the parent of {object}.",
          "examples": [
                       "{Debbie Reynolds} said [her daughter] was in a better place now.",
          ],
          "image": "parents.png", 
          "icon": "fa-child",
          "subject-types": ["PER"],
          "object-types": ["PER"]
      },{
          "name": "per:spouse",
          "short": "spouse",
          "template": "{subject} is/was the spouse of {object}.",
          "image": "spouse.svg", 
          "examples": [
                       "{Barack Obama} thanked his wife, [Michelle].",
          ],
          "icon": "fa-diamond",
          "subject-types": ["PER"],
          "object-types": ["PER"]
      },{
          "name": "per:siblings",
          "short": "sibling of",
          "template": "{subject} is the sibling of {object}.",
          "image": "sibling.png", 
          "examples": [
                       "Obama said he was proud of his daughters {Malia} and [Sasha].",
          ],
          "icon": "fa-child",
          "subject-types": ["PER"],
          "object-types": ["PER"]
      },{
          "name": "per:other_family",
          "short": "other family",
          "template": "{subject} and {object} are otherwise family.",
          "examples": ["Grandparents, cousins and uncles would be considered as other family."],
          "image": "other_family.png", 
          "icon": "fa-child",
          "subject-types": ["PER"],
          "object-types": ["PER"]
      },{
          "name": "per:title",
          "short": "professional title",
          "image": "", 
          "icon": "fa-id-card-o",
          "examples": [
                       "Official [spokesperson] {Shayne Williams}",
                       "[Wife] is NOT a title."
          ],
          "template": "{subject} is/was a {object}.",
          "subject-types": ["PER"],
          "object-types": ["TITLE"]
      // },{
      //     "name": "org:alternate_names",
      //     "short": "alias",
      //     "image": "alternate_names.svg", 
      //     "icon": "fa-address-book",
      //     "template": "{subject} is also known as {object}.",
      //     "examples": ["{Quantum Computer Services} was renamed [Americal Online]"],
      //     "subject-types": ["ORG"],
      //     "object-types": ["ORG"]
      },{
          "name": "org:place_of_headquarters",
          "short": "headquartered at",
          "template": "{subject} is/was headquartered at {object}.",
          "examples": [
            "[Singapore]-based {Flextronics}...",
            "A company is NOT headquartered in a city if it only has an office there.",
          ],
          "image": "", 
          "icon": "fa-building-o",
          "subject-types": ["ORG"],
          "object-types": ["GPE"]
      },{
          "name": "org:date_founded",
          "short": "founded on",
          "template": "{subject} was founded on {object}.",
          "examples": [
            "Steve Jobs founded {Apple Inc.} in [1976].",
          ],
          "image": "founder.svg", 
          "icon": "fa-building",
          "subject-types": ["ORG"],
          "object-types": ["DATE"]
      },{
          "name": "org:date_dissolved",
          "short": "dissolved on",
          "template": "{subject} was closed/dissolved on {object}.",
          "image": "", 
          "examples": [
            "{Lehman Brothers} was sold to Nomura and Barclays in [2008].",
          ],
          "icon": "fa-trash-o",
          "subject-types": ["ORG"],
          "object-types": ["DATE"]
      },{
          "name": "org:founded_by",
          "short": "founded by",
          "template": "{subject} was founded by {object}.",
          "examples": [
            "{The association} was started by [Walmart].",
          ],
          "image": "founder.svg", 
          "icon": "fa-black-tie",
          "subject-types": ["ORG"],
          "object-types": ["ORG", "GPE"]
      },{
          "name": "org:member_of",
          "short": "member of",
          "template": "{subject} is/was a member of {object}, though {subject} can operate independently of {object}.",
          "image": "members.jpg", 
          "examples": ["{Golden State Warriors} is a member of the [NBA]."],
          "icon": "fa-users",
          "subject-types": ["ORG"],
          "object-types": ["ORG", "GPE"]
      },{
          "name": "org:members",
          "short": "has member",
          "template": "{subject} has/had {object} as a member, though {object} can operate independently of {subject}.",
          "image": "members.jpg", 
          "examples": ["The {United Nations} has the [United States] as a member",
                       "The {American Humane Society} has [Clover Farms] as a member"],
          "icon": "fa-users",
          "subject-types": ["ORG"],
          "object-types": ["ORG", "GPE"]
      },{
          "name": "org:subsidiaries",
          "short": "parent of",
          "template": "{subject} owns/owned {object} and {object} can not exist without {subject}.",
          "image": "", 
          "examples": [
              "{Fox Entertainment Group} is the parent of [Fox News].",
              "{Google} is the parent of Google's [Board of Directors]."],
          "icon": "fa-sitemap",
          "subject-types": ["ORG"],
          "object-types": ["ORG"]
      },{
          "name": "org:parents",
          "short": "subsidiary of",
          "template": "{subject} is/was a subsidiary of {object} and {subject} can not exist without {object}.",
          "image": "", 
          "examples": ["The {Department of Homeland Security} is a subsidiary of the [U.S.]."],
          "icon": "fa-sitemap",
          "subject-types": ["ORG"],
          "object-types": ["ORG", "GPE"]
      },{
          "name": "org:shareholders",
          "short": "shareholder",
          "template": "{object} is/was a shareholder of {subject}.",
          "image": "shareholders.png", 
          "examples": [],
          "icon": "fa-line-chart",
          "subject-types": ["ORG"],
          "object-types": ["ORG", "GPE"]
      },{
          "name": "org:holds_shares_in",
          "short": "holds shares in",
          "template": "{subject} holds/held shares in {object}.",
          "image": "shareholders.png", 
          "examples": [],
          "icon": "fa-line-chart",
          "subject-types": ["ORG"],
          "object-types": ["ORG"]
      // ignoring org:employees_or_members -- we have per:employee_or_member_of
      // ignoring org:students -- we have per:schools_attended 
    }];

    var RelationLabel = function(r) {
        this.name = r.name;
        this.short = r.short;
        this.icon = r.icon;
        this.image = r.image;
        this.examples = r.examples;
        this.template = r.template;
        this.subjectTypes = r["subject-types"];
        this.objectTypes = r["object-types"];
    };

    RelationLabel.prototype.renderTemplate = function(mentionPair, useLink) {
        if (useLink === undefined){
            useLink = false;
        }
        var subject = (useLink && mentionPair.subject.entity.gloss) ? mentionPair.subject.entity.gloss : mentionPair.subject.gloss;
        var object = (useLink && mentionPair.object.entity.gloss) ? mentionPair.object.entity.gloss : mentionPair.object.gloss;
        return this.template
            .replaceAll("{subject}", "<span class='subject'>" + subject + "</span>")
            .replaceAll("{object}", "<span class='object'>" + object + "</span>");
    };

    RelationLabel.prototype.isApplicable = function(mentionPair) {
        return this.subjectTypes.indexOf(mentionPair.subject.type.name) >= 0 && 
            this.objectTypes.indexOf(mentionPair.object.type.name) >= 0;
    };

    var RELATIONS = [];
    var RELATION_MAP = [];
    _RELATIONS.forEach(function(r) {RELATIONS.push(new RelationLabel(r));});
    _RELATIONS.forEach(function(r) {RELATION_MAP[r.name] = new RelationLabel(r);});

    var _TYPES = [
      {
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
      }
    ];
    var EntityType = function(t) {
        this.name = t.name;
        this.gloss = t.gloss;
        this.icon = t.icon;
    };
    var TYPES = {};
    _TYPES.forEach(function(t) {TYPES[t.name] = t;});

    // 
    var Mention = function(m) {
        this.id = Mention.count++;
        if (typeof m.type == "string") {
          this.type = m.type && TYPES[m.type];
        } else {
          this.type = m.type && m.type.name && TYPES[m.type.name];
        }
        this.gloss = m.gloss;
        this.span = m.span;

        this.entity = m.entity; // can be undefined.

      // this.tokens = m.tokens;
      // this.sentenceIdx = m.sentenceIdx || m.tokens[0].sentenceIdx;
    };
    Mention.count = 0;
    Mention.fromTokens = function(tokens) {
      let m = new Mention({
               "type": undefined,
               "gloss": Mention.textFromTokens(tokens),
               "span": tokens[0].token.span,
        });
      m.setTokens(tokens);
      m.setSentenceIdx(tokens[0].sentenceIdx);
      return m;
    };

    Mention.fromJSON = function(m, doc) {
      let mention = new Mention(m);
      doc.addMention(mention);

      if (m.entity !== undefined) {
        // uh, create a new canonical mention and make it an entity.
        let canonicalMention = new Mention(m.entity);
        doc.addMention(canonicalMention);

        canonicalMention.link = m.entity.link;
        mention.entity = new Entity(canonicalMention);
      }
      return mention;
    };

    Mention.textFromTokens = function(tokens) {
        text = "";
        for (i = 0; i < tokens.length; i++){
          if (tokens[i].classList.contains("with-space")) {
            text += " ";
          }
          text += tokens[i].textContent;
        }
        return text;
    };

    Mention.prototype.setTokens = function(tokens) {
      this.tokens = tokens;
    }
    Mention.prototype.setSentenceIdx = function(sentenceIdx) {
      this.sentenceIdx = sentenceIdx;
    }
    Mention.prototype.setElem = function(elem) {
      this.elem = elem;
    }
    // Compute levenshtein distance from input @string
    Mention.prototype.levenshtein = function(string){
        temp = this;
        
        var first_words = this.gloss.trim().toLowerCase().split(/\s+/);
        var second_words = string.trim().split(/\s+/);
        var min_distance = 1000;
        for(var i=0;i<first_words.length; i++){
            for(var j=0;j<second_words.length; j++){
                var distance = Levenshtein.get($.trim(first_words[i]), $.trim(second_words[j]));
                if(distance < min_distance){
                    min_distance = distance;
                }
            }
        }
        return min_distance;
    };

    Mention.prototype.toJSON = function() {
        var val = {
            "gloss": this.gloss,
                "type": this.type.name,
                "span": this.span,
                "entity": (this.entity) ? {
                    "gloss": this.entity.gloss,
                    "type": this.type.name,
                    "link": this.entity.link,
                    "span": this.entity.span,
                    "canonicalCorrect": this.canonicalCorrect, 
                    "linkGold": this.linkGold,
                } : null
        };
        if (this.entity.canonicalCorrect !== undefined){
            val.entity.canonicalCorrect = this.entity.canonicalCorrect;
        }
        if (this.entity.linkGold !== undefined){
            val.entity.linkGold = this.entity.linkGold;
        }
        return val;
    };

    // Creates a new entity from a @canonical_mention and @type.
    function Entity(canonicalMention) {
        this.idx = 1 + Entity.count++;
        this.id = "e-" + this.idx;
        this.gloss = canonicalMention.gloss;
        this.type = canonicalMention.type;
        this.span = canonicalMention.span;
        this.mentions = [];
        this.link = canonicalMention.link;

        this.addMention(canonicalMention);
    }
    Entity.count = 0;
    Entity.map = {};

    Entity.prototype.addMention = function(mention) {
      console.info("Adding mention", mention.gloss, "to", this.gloss);
      // Set the type of the mention if it hasn't already been set.
      if (mention.type === null) {
        mention.type = this.type;
      }
      mention.entity = this;

      this.mentions.push(mention);
      Entity.map[mention.id] = this;
    };

    // Returns "true" if the mention has > 0 mentions.
    Entity.prototype.removeMention = function(mention) {
        console.info("Removing mention ", mention);
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
        var lowerMentionText = mentionText.toLowerCase();
        var bestMatch = null;
            var bestScore = 1000;
        for (var i = 0; i < this.mentions.length; i++) {
            var score = this.mentions[i].levenshtein(lowerMentionText);
            if (bestScore > score && this.mentions[i].tokens[0].token.pos_tag != "PRP") {
                bestScore = score;
                bestMatch = this.mentions[i];
            }
        }
        return bestScore;
    };

    return {
        'RELATIONS': RELATIONS,
        'RELATION_MAP': RELATION_MAP,
        'TYPES': TYPES,
        'Mention': Mention,
        'Entity': Entity,
    };
});
