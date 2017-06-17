"""
Definitions for the KBPO task.
"""

# MAKE SURE THIS CORRESPONDS WITH sql/functions.sql:to_kbpo_type.
NER_MAP = {
    "PERSON": "PER",
    "ORGANIZATION": "ORG",
    "GPE": "GPE",
    "CITY": "GPE",
    "STATE_OR_PROVINCE": "GPE",
    "COUNTRY": "GPE",
    "LOCATION": "GPE",
    "TITLE": "TITLE",
    "DATE": "DATE",
    }
TYPES = list(NER_MAP.values())
ENTITY_SLOT_TYPES = set(["PER", "ORG", "GPE"])
STRING_SLOT_TYPES = set(["DATE", "TITLE"])
assert len((ENTITY_SLOT_TYPES | STRING_SLOT_TYPES) ^ set(TYPES)) == 0, "Inconsistency"

# NOTE: We excluding alternate_names from consideration because (a) they
# are replicated by entity linking, (b) it confuses turkers and (c) it's
# a stupid relation anyways.
RELATION_MAP = {
    #"per:alternate_names":"per:alternate_names",

    "per:place_of_birth":"per:place_of_birth",
    "per:city_of_birth":"per:place_of_birth",
    "per:stateorprovince_of_birth":"per:place_of_birth",
    "per:country_of_birth":"per:place_of_birth",

    "per:place_of_residence":"per:place_of_residence",
    "per:cities_of_residence":"per:place_of_residence",
    "per:stateorprovinces_of_residence":"per:place_of_residence",
    "per:countries_of_residence":"per:place_of_residence",

    "per:place_of_death":"per:place_of_death",
    "per:city_of_death":"per:place_of_death",
    "per:stateorprovince_of_death":"per:place_of_death",
    "per:country_of_death":"per:place_of_death",

    "per:date_of_birth":"per:date_of_birth",
    "per:date_of_death":"per:date_of_death",
    "per:organizations_founded":"per:organizations_founded",
    "per:holds_shares_in":"per:holds_shares_in",
    "per:schools_attended":"per:schools_attended",
    "per:top_member_employee_of":"per:employee_or_member_of",
    "per:employee_or_member_of":"per:employee_or_member_of",
    "per:parents":"per:parents",
    "per:children":"per:children",
    "per:spouse":"per:spouse",
    "per:siblings":"per:siblings",
    "per:other_family":"per:other_family",
    "per:title":"per:title",

    #"org:alternate_names":"org:alternate_names",

    "org:place_of_headquarters":"org:place_of_headquarters",
    "org:city_of_headquarters":"org:place_of_headquarters",
    "org:stateorprovince_of_headquarters":"org:place_of_headquarters",
    "org:country_of_headquarters":"org:place_of_headquarters",

    "org:date_founded":"org:date_founded",
    "org:date_dissolved":"org:date_dissolved",
    "org:founded_by":"org:founded_by",
    "org:organizations_founded":"org:organizations_founded",
    "org:member_of":"org:member_of",
    "org:top_members_employees": "org:employees_or_members",
    "org:employees_or_members": "org:employees_or_members",
    "org:members":"org:members",
    "org:subsidiaries":"org:subsidiaries",
    "org:parents":"org:parents",
    "org:shareholders":"org:shareholders",
    "org:holds_shares_in":"org:holds_shares_in",
    "org:students": "org:students",

    "gpe:births_in_place":"gpe:births_in_place",
    "gpe:births_in_city":"gpe:births_in_place",
    "gpe:births_in_stateorprovince":"gpe:births_in_place",
    "gpe:births_in_country":"gpe:births_in_place",

    "gpe:residents_in_place": "gpe:residents_in_place",
    "gpe:residents_of_city": "gpe:residents_in_place",
    "gpe:residents_of_stateorprovince": "gpe:residents_in_place",
    "gpe:residents_of_country": "gpe:residents_in_place",

    "gpe:deaths_in_place": "gpe:deaths_in_place",
    "gpe:deaths_in_city": "gpe:deaths_in_place",
    "gpe:deaths_in_stateorprovince": "gpe:deaths_in_place",
    "gpe:deaths_in_country": "gpe:deaths_in_place",

    "gpe:employees_or_members": "gpe:employees_or_members",
    "gpe:holds_shares_in": "gpe:holds_shares_in",
    "gpe:organizations_founded": "gpe:organizations_founded",
    "gpe:member_of": "gpe:member_of",

    "gpe:headquarters_in_place":"gpe:headquarters_in_place",
    "gpe:headquarters_in_city":"gpe:headquarters_in_place",
    "gpe:headquarters_in_stateorprovince":"gpe:headquarters_in_place",
    "gpe:headquarters_in_country":"gpe:headquarters_in_place",

    "no_relation":"no_relation",
    }
ALL_RELATIONS = list(RELATION_MAP.values())
RELATIONS = [
    #"per:alternate_names",
    "per:place_of_birth",
    "per:place_of_residence",
    "per:place_of_death",
    "per:date_of_birth",
    "per:date_of_death",
    "per:organizations_founded",
    "per:holds_shares_in",
    "per:schools_attended",
    "per:employee_or_member_of",
    "per:parents",
    "per:children",
    "per:spouse",
    "per:siblings",
    "per:other_family",
    "per:title",
    #"org:alternate_names",
    "org:place_of_headquarters",
    "org:date_founded",
    "org:date_dissolved",
    "org:founded_by",
    "org:member_of",
    "org:members",
    "org:subsidiaries",
    "org:parents",
    "org:shareholders",
    "org:holds_shares_in",
    "org:employees_or_members",
    "org:students",
    "no_relation",
    ]

INVERTED_RELATIONS = {
    "per:children":["per:parents"],
    "per:other_family":["per:other_family"],
    "per:parents":["per:children"],
    "per:siblings":["per:siblings"],
    "per:spouse":["per:spouse"],
    "per:employee_or_member_of":["org:employees_or_members","gpe:employees_or_members"],
    "per:schools_attended":["org:students"],
    "per:place_of_birth":["gpe:births_in_place"],
    "per:place_of_residence":["gpe:residents_in_place"],
    "per:place_of_death":["gpe:deaths_in_place"],
    "per:organizations_founded":["org:founded_by"],
    "per:holds_shares_in":["org:shareholders"],

    "org:shareholders":["per:holds_shares_in","org:holds_shares_in","gpe:holds_shares_in"],
    "org:holds_shares_in":["org:shareholders"],
    "org:founded_by":["per:organizations_founded","org:organizations_founded","gpe:organizations_founded"],
    "org:organizations_founded":["org:founded_by",],
    "org:employees_or_members": ["per:employee_or_member_of"],
    "org:member_of":["org:members"],
    "org:members":["gpe:member_of","org:member_of"],
    "org:students":["per:schools_attended"],
    "org:subsidiaries":["org:parents"],
    "org:parents":["org:subsidiaries"],
    "org:place_of_headquarters":["gpe:headquarters_in_place"],

    "gpe:births_in_place":["per:place_of_birth"],
    "gpe:residents_in_place":["per:place_of_residence"],
    "gpe:deaths_in_place":["per:place_of_death"],
    "gpe:employees_or_members": ["per:employee_or_member_of"],
    "gpe:holds_shares_in":["org:shareholders"],
    "gpe:organizations_founded":["org:founded_by",],
    "gpe:member_of":["org:members"],
    "gpe:headquarters_in_place":["org:place_of_headquarters"],
    }

RELATION_TYPES = {
    "per:alternate_names": ("PER", "PER"),
    "per:place_of_birth": ("PER", "GPE"),
    "per:place_of_residence": ("PER", "GPE"),
    "per:place_of_death": ("PER", "GPE"),
    "per:date_of_birth": ("PER", "DATE"),
    "per:date_of_death": ("PER", "DATE"),
    "per:organizations_founded": ("PER", "ORG"),
    "per:holds_shares_in": ("PER", "ORG"),
    "per:schools_attended": ("PER", "ORG"),
    "per:employee_or_member_of": ("PER", ["ORG", "GPE"]),
    "per:parents": ("PER", "PER"),
    "per:children": ("PER", "PER"),
    "per:spouse": ("PER", "PER"),
    "per:siblings": ("PER", "PER"),
    "per:other_family": ("PER", "PER"),
    "per:title": ("PER", "TITLE"),
    "org:alternate_names": ("ORG", "ORG"),
    "org:place_of_headquarters": ("ORG", "GPE"),
    "org:date_founded": ("ORG", "DATE"),
    "org:date_dissolved": ("ORG", "DATE"),
    "org:founded_by": ("ORG", ["PER", "ORG", "GPE"]),
    "org:member_of": ("ORG", "ORG"),
    "org:members": ("ORG", ["ORG", "GPE"]),
    "org:subsidiaries": ("ORG", "ORG"),
    "org:parents": ("ORG", "ORG"),
    "org:shareholders": ("ORG", ["PER", "ORG", "GPE"]),
    "org:holds_shares_in": ("ORG", "ORG"),
    "org:employees_or_members": ("ORG", "PER"),
    "org:students": ("ORG", "PER"),
}
STRING_VALUED_RELATIONS = {}
for k,v in RELATION_TYPES.items():
    t = set([v[1]]) if not isinstance(v[1], list) else set(v[1])
    string_types = t & STRING_SLOT_TYPES
    if len(string_types) != 0:
        assert len(string_types) == 1
        STRING_VALUED_RELATIONS[k] = list(string_types)[0]

#Special case where the string valued slow actually refers to an entity
STRING_VALUED_RELATIONS['per:alternate_names'] = 'PER'
STRING_VALUED_RELATIONS['org:alternate_names'] = 'ORG'
#print(STRING_VALUED_RELATIONS)

def _create_mention_types(types):
    valid_types = set()
    for subject_, objects in types.values():
        if isinstance(objects, str):
            objects = [objects]
        for object_ in objects:
            # Strict type hierarchy -- prefer PER over ORG over GPE
            if subject_ == "ORG" and object_ == "PER":
                continue
            if subject_ == "GPE" and object_ == "ORG":
                continue
            if subject_ == "GPE" and object_ == "PER":
                continue

            valid_types.add((subject_, object_))
    return valid_types

VALID_MENTION_TYPES = _create_mention_types(RELATION_TYPES)

def standardize_relation(subject, subject_type, reln, object_, object_type):
    if reln in RELATIONS:
        return subject, subject_type, reln, object_, object_type
    elif reln not in RELATIONS and reln in INVERTED_RELATIONS:
        for reln_ in INVERTED_RELATIONS[reln]:
            if reln_.startswith(object_type.lower()):
                return object_, object_type, reln, subject, subject_type
    else:
        raise ValueError("Couldn't map relation for {} {} {}".format(subject_type, reln, object_type))
