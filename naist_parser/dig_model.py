from sqlobject import *

sqlhub.processConnection = connectionForURI("mysql://khem:v,8;ps,k@vivaldi.cpe.ku.ac.th:3306/nonyipuk")

class DigHead(SQLObject):
    """ Head representation
    """
    head = StringCol(notNone=True,length=100)    # Head of elementary tree
    type = EnumCol(enumValues=["I","II","III"])  # Type of elementary tree
    etype = EnumCol(enumValues=["S","G"]) # S = Specific, G = Generic
    rules = MultipleJoin("DigRule",joinColumn='dighead_id')

class DigRule(SQLObject):
    """ Rule representation
    """
    rule = StringCol(notNone=True)    # Elementary tree
    n = IntCol(notNone=True)     # A number of elementary
    dighead = ForeignKey("DigHead", cascade=True)
    indexes = MultipleJoin("DigIndex",joinColumn='digrule_id')

class DigIndex(SQLObject):
    """ Index representation
    """
    word_order = StringCol(notNone=True)   # Word ordering
    n = IntCol(notNone=True)          # A number of word ordering
    digrule = ForeignKey("DigRule", cascade=True)
    dig_trees = RelatedJoin("DigTree")

class DigTree(SQLObject):
    """ Tree representation
    """
    tree = StringCol(notNone=True)     # Original tree 
    tree_number = IntCol(notNone=True)
    dig_indexes = RelatedJoin("DigIndex")

