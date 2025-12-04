"""Unit tests for the equation solver API."""

from __future__ import annotations

import pytest

from app import create_app, parse_equation, solve_equation, _solve_cached


@pytest.fixture(autouse=True)
def clear_caches():
    """Clear caches before each test."""
    _solve_cached.cache_clear()
    parse_equation.cache_clear()
    yield
    _solve_cached.cache_clear()
    parse_equation.cache_clear()


@pytest.fixture
def client():
    """Create Flask test client."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestParseEquation:
    """Test parse_equation function."""

    def test_simple_expression(self):
        """Test parsing simple expression."""
        expr, symbols = parse_equation("x + 1")
        assert len(symbols) == 1
        assert "x" in [str(s) for s in symbols]

    def test_multiple_variables(self):
        """Test parsing expression with multiple variables."""
        expr, symbols = parse_equation("x + y + z")
        assert len(symbols) == 3

    def test_implicit_multiplication(self):
        """Test implicit multiplication parsing."""
        expr, symbols = parse_equation("2x")
        assert len(symbols) == 1


class TestSolveEquation:
    """Test solve_equation function with various cases."""

    def test_linear_equation(self):
        """Test solving linear equation."""
        result = solve_equation("2*x + 3 = 7")
        assert "result" in result
        assert "x = 2" in result["result"]

    def test_quadratic_equation(self):
        """Test solving quadratic equation."""
        result = solve_equation("x**2 - 5*x + 6 = 0")
        assert "result" in result
        assert "2" in result["result"] and "3" in result["result"]

    def test_expression_without_equals(self):
        """Test solving expression (assumed = 0)."""
        result = solve_equation("x**2 + 2*x - 10")
        assert "result" in result

    def test_simple_arithmetic(self):
        """Test simple arithmetic without variables."""
        result = solve_equation("2 + 2")
        assert "result" in result
        assert "4" in result["result"]

    def test_division(self):
        """Test equation with division."""
        result = solve_equation("x / 2 = 5")
        assert "result" in result
        assert "10" in result["result"]

    def test_square_root(self):
        """Test equation with square root."""
        result = solve_equation("x**2 = 16")
        assert "result" in result

    def test_no_solution(self):
        """Test equation with no solution."""
        result = solve_equation("x + 1 = x + 2")
        assert "result" in result

    def test_invalid_syntax(self):
        """Test invalid equation syntax."""
        result = solve_equation("x +* 2")
        assert "error" in result

    def test_empty_equation(self):
        """Test with empty string - handled by endpoint."""
        result = solve_equation("")
        assert "error" in result

    def test_complex_polynomial(self):
        """Test complex polynomial."""
        result = solve_equation("x**3 - 6*x**2 + 11*x - 6 = 0")
        assert "result" in result

    def test_exponential(self):
        """Test exponential equation."""
        result = solve_equation("2**x = 8")
        assert "result" in result

    def test_trigonometric(self):
        """Test trigonometric equation."""
        result = solve_equation("sin(x) = 0")
        assert "result" in result

    def test_multiple_variables_equation(self):
        """Test equation with multiple variables."""
        result = solve_equation("x + y = 10")
        assert "result" in result

    def test_fraction(self):
        """Test equation with fractions."""
        result = solve_equation("x/3 + x/2 = 5")
        assert "result" in result


class TestAPIEndpoints:
    """Test Flask API endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns welcome message."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data

    def test_solve_endpoint_with_equation(self, client):
        """Test solve endpoint with valid equation."""
        response = client.get("/solve?equation=x+1=2")
        assert response.status_code == 200
        data = response.get_json()
        assert "result" in data

    def test_solve_endpoint_without_equation(self, client):
        """Test solve endpoint without equation parameter."""
        response = client.get("/solve")
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_solve_endpoint_with_empty_equation(self, client):
        """Test solve endpoint with empty equation."""
        response = client.get("/solve?equation=")
        assert response.status_code == 400

    def test_solve_endpoint_quadratic(self, client):
        """Test solve endpoint with quadratic equation."""
        response = client.get("/solve?equation=x**2-4=0")
        assert response.status_code == 200
        data = response.get_json()
        assert "result" in data

    def test_solve_endpoint_invalid_syntax(self, client):
        """Test solve endpoint with invalid syntax."""
        response = client.get("/solve?equation=x%2B*2")  # x+*2 with proper encoding
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_cors_headers(self, client):
        """Test CORS headers are set."""
        response = client.get("/")
        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "*"

    def test_solve_endpoint_arithmetic(self, client):
        """Test arithmetic evaluation."""
        response = client.get("/solve?equation=10%2B5")  # %2B is URL encoding for +
        assert response.status_code == 200
        data = response.get_json()
        assert "result" in data
        assert "15" in data["result"]

    def test_solve_endpoint_special_characters(self, client):
        """Test equation with special URL characters."""
        response = client.get("/solve?equation=x%2B1%3D2")  # x+1=2 encoded
        assert response.status_code == 200
