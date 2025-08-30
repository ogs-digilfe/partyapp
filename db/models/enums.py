from enum import Enum

class LawType(str, Enum):
    constitution = "constitution"
    statute = "statute"
    cabinet_order = "cabinet_order"
    ministerial_order = "ministerial_order"
    national_rule = "national_rule"
    ordinance = "ordinance"
    local_rule = "local_rule"

class JurisdictionLevel(str, Enum):
    national = "national"
    local = "local"

class PartyRole(str, Enum):
    submitter = "submitter"
    co_submitter = "co_submitter"
    cabinet = "cabinet"
    coalition = "coalition"
    voted_for = "voted_for"
    voted_against = "voted_against"

class CategoryType(str, Enum):
    politics = "politics"
    economy = "economy"
    international = "international"
    environment_science = "environment_science"
    culture = "culture"
    life_medical = "life_medical"
    society = "society"