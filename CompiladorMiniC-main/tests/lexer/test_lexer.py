"""Pruebas unitarias para el analizador léxico de Mini C.

Verifican el cumplimiento estricto de SKILL.md y del capítulo IV (§4.4 de la SRS):
- Alfabeto, palabras reservadas y patrones.
- Prioridades (keywords > identifier, == > =).
- Políticas de separación (máxima coincidencia, 12abc, -5).
- Cálculo de posiciones (1-based, \\t = 1 col, solo \\n reinicia col).
- Diagnóstico LEX001 y recuperación.
- Emisión única de EOF.
"""

from minic.diagnostics.diagnostic_code import LEX001
from minic.lexer import Lexer, TokenType
from minic.output import format_diagnostic, format_token


def test_skill_section_7_valid_case() -> None:
    source = "int2 = 12abc;\nwhilex == -5"
    lexer = Lexer(source)
    tokens, diagnostics = lexer.scan()

    assert len(diagnostics) == 0

    expected = [
        (TokenType.IDENTIFIER, "int2", None, 1, 1),
        (TokenType.ASSIGN, "=", None, 1, 6),
        (TokenType.INTEGER_LITERAL, "12", 12, 1, 8),
        (TokenType.IDENTIFIER, "abc", None, 1, 10),
        (TokenType.SEMICOLON, ";", None, 1, 13),
        (TokenType.IDENTIFIER, "whilex", None, 2, 1),
        (TokenType.EQUAL_EQUAL, "==", None, 2, 8),
        (TokenType.MINUS, "-", None, 2, 11),
        (TokenType.INTEGER_LITERAL, "5", 5, 2, 12),
        (TokenType.EOF, "", None, 2, 13),
    ]

    assert len(tokens) == len(expected)
    for token, (t_type, lexeme, literal, line, col) in zip(tokens, expected):
        assert token.type == t_type
        assert token.lexeme == lexeme
        assert token.literal == literal
        assert token.line == line
        assert token.column == col

    formatted = [format_token(t) for t in tokens]
    expected_formatted = [
        "IDENTIFIER 'int2' 1 1",
        "ASSIGN '=' 1 6",
        "INTEGER_LITERAL '12' 1 8",
        "IDENTIFIER 'abc' 1 10",
        "SEMICOLON ';' 1 13",
        "IDENTIFIER 'whilex' 2 1",
        "EQUAL_EQUAL '==' 2 8",
        "MINUS '-' 2 11",
        "INTEGER_LITERAL '5' 2 12",
        "EOF '' 2 13",
    ]
    assert formatted == expected_formatted


def test_skill_section_7_errors_case() -> None:
    source = "int x = @;\nx ! = 0; // fin"
    lexer = Lexer(source)
    tokens, diagnostics = lexer.scan()

    # Tokens esperados
    expected_tokens = [
        (TokenType.KW_INT, "int", None, 1, 1),
        (TokenType.IDENTIFIER, "x", None, 1, 5),
        (TokenType.ASSIGN, "=", None, 1, 7),
        (TokenType.SEMICOLON, ";", None, 1, 10),
        (TokenType.IDENTIFIER, "x", None, 2, 1),
        (TokenType.ASSIGN, "=", None, 2, 5),
        (TokenType.INTEGER_LITERAL, "0", 0, 2, 7),
        (TokenType.SEMICOLON, ";", None, 2, 8),
        (TokenType.IDENTIFIER, "fin", None, 2, 13),
        (TokenType.EOF, "", None, 2, 16),
    ]

    assert len(tokens) == len(expected_tokens)
    for token, (t_type, lexeme, literal, line, col) in zip(tokens, expected_tokens):
        assert token.type == t_type
        assert token.lexeme == lexeme
        assert token.literal == literal
        assert token.line == line
        assert token.column == col

    # Diagnósticos esperados
    assert len(diagnostics) == 4
    formatted_diag = [format_diagnostic(d) for d in diagnostics]
    expected_diag = [
        "LEX001 error 1:9 Carácter no reconocido: '@'",
        "LEX001 error 2:3 Carácter no reconocido: '!'",
        "LEX001 error 2:10 Carácter no reconocido: '/'",
        "LEX001 error 2:11 Carácter no reconocido: '/'",
    ]
    assert formatted_diag == expected_diag


def test_keywords_vs_identifiers() -> None:
    source = "int integer _int while while1"
    tokens, diagnostics = Lexer(source).scan()
    assert len(diagnostics) == 0

    token_types = [t.type for t in tokens[:-1]]
    assert token_types == [
        TokenType.KW_INT,
        TokenType.IDENTIFIER,
        TokenType.IDENTIFIER,
        TokenType.KW_WHILE,
        TokenType.IDENTIFIER,
    ]


def test_operator_maximal_munch() -> None:
    source = "== = != !"
    tokens, diagnostics = Lexer(source).scan()

    # '!' solo no existe en Mini C, produce LEX001
    assert len(diagnostics) == 1
    assert diagnostics[0].code == LEX001
    assert diagnostics[0].line == 1
    assert diagnostics[0].column == 9

    assert [t.type for t in tokens] == [
        TokenType.EQUAL_EQUAL,
        TokenType.ASSIGN,
        TokenType.NOT_EQUAL,
        TokenType.EOF,
    ]


def test_integer_literal_values() -> None:
    source = "0 007 123456"
    tokens, diagnostics = Lexer(source).scan()
    assert len(diagnostics) == 0

    assert [(t.lexeme, t.literal) for t in tokens[:-1]] == [
        ("0", 0),
        ("007", 7),
        ("123456", 123456),
    ]


def test_tab_and_newline_positions() -> None:
    # \t cuenta como 1 columna
    source = "\tint\n\tx"
    tokens, diagnostics = Lexer(source).scan()
    assert len(diagnostics) == 0

    # línea 1: '\t' ocupa col 1 -> 'int' inicia en col 2
    assert tokens[0].line == 1
    assert tokens[0].column == 2

    # línea 2: '\t' ocupa col 1 -> 'x' inicia en col 2
    assert tokens[1].line == 2
    assert tokens[1].column == 2


def test_empty_source() -> None:
    tokens, diagnostics = Lexer("").scan()
    assert len(diagnostics) == 0
    assert len(tokens) == 1
    assert tokens[0].type == TokenType.EOF
    assert tokens[0].lexeme == ""
    assert tokens[0].literal is None
    assert tokens[0].line == 1
    assert tokens[0].column == 1
