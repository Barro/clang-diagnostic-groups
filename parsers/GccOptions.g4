grammar GccOptions;

options
{
    language = Python2;
}

optionAttributes : optionAttribute (SPACE optionAttribute)* SPACE? EOF ;

optionAttribute : variableName trailer? ;

variableName : NAME_LITERAL ;

trailer : OPEN_PAREN argumentList? CLOSE_PAREN ;

argumentList : argument (COMMA SPACE* argument)* ;

argument : ternary ;

ternary
   :<assoc=right> ternary SPACE* '?' SPACE* ternary SPACE* ':' SPACE* ternary
   | orTest ;

orTest : andTest (SPACE* OR SPACE* andTest)* ;

OR : '||' ;

andTest : comparison (SPACE* AND SPACE* comparison)* ;

AND : '&&' ;

comparison : atomlist (SPACE* compOp SPACE* atomlist)* ;

compOp
    : '>='
    ;

atomlist : atom (SPACE atom)* ;

atom
    :
    INTEGER_LITERAL
    | NAME_LITERAL
    | PERCENTAGE_LITERAL
    | WARNING_TEXT_LITERAL
    ;

WARNING_TEXT_LITERAL : '{' ('a'..'z' | 'A'..'Z' | '-' | '(' | ')' | '%' | ' ')+ '}' ;

INTEGER_LITERAL : '-'? INTEGERCHAR+ ;

NAME_LITERAL : ('a'..'z' | 'A'..'Z' | '-') ( 'a'..'z' | 'A'..'Z' | '0'..'9' | '=' | '-' | '+' | '_' | '.')* ;

PERCENTAGE_LITERAL : '%' ('a'..'z' | '<' | '>')+ ;

INTEGERCHAR : '0'..'9' ;

COMMA : ',' ;

OPEN_PAREN : '(' ;

CLOSE_PAREN : ')' ;

FUNCTIONCHAR : 'a'..'z' | 'A'..'Z' ;

SPACE : ' ' ;
