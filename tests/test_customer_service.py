"""Tests for customer service (save/list/delete)."""
import os
import tempfile
import pytest

_tmpdir = tempfile.mkdtemp()
os.environ.setdefault("LOJAFLOW_DATA", _tmpdir)

from app.database import init_db
from app.views.customers.customers_view import delete_customer, list_customers, save_customer


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield


def _make_customer(**kwargs):
    defaults = {"name": "Cliente Teste", "phone": "", "cpf": "", "email": "", "notes": ""}
    defaults.update(kwargs)
    return save_customer(None, defaults)


class TestSaveCustomer:
    def test_create_customer(self):
        c = _make_customer(name="João Silva", phone="(11) 99999-9999")
        assert c.id is not None
        assert c.name == "João Silva"
        assert c.phone == "(11) 99999-9999"

    def test_create_with_cpf(self):
        c = _make_customer(name="Maria", cpf="123.456.789-00")
        assert c.cpf == "123.456.789-00"

    def test_create_with_null_fields(self):
        """Campos opcionais como phone/cpf devem aceitar string vazia."""
        c = _make_customer(name="Cliente Simples", phone="", cpf="", notes="")
        assert c.id is not None

    def test_update_customer(self):
        c = _make_customer(name="Carlos Antigo")
        updated = save_customer(c.id, {"name": "Carlos Novo", "phone": "", "cpf": "", "email": "", "notes": ""})
        assert updated.name == "Carlos Novo"

    def test_update_nonexistent_raises(self):
        with pytest.raises(ValueError, match="não encontrado"):
            save_customer(99999, {"name": "Ghost", "phone": "", "cpf": "", "email": "", "notes": ""})


class TestListCustomers:
    def test_list_all(self):
        _make_customer(name="Ana")
        _make_customer(name="Bia")
        customers = list_customers()
        names = [c.name for c in customers]
        assert "Ana" in names
        assert "Bia" in names

    def test_search_by_name(self):
        _make_customer(name="Pedro Alvares")
        _make_customer(name="Marcos Vinicius")
        results = list_customers("Pedro")
        assert any("Pedro" in c.name for c in results)
        assert not any("Marcos" in c.name for c in results)

    def test_search_by_phone(self):
        _make_customer(name="Luiz", phone="(21) 88888-8888")
        _make_customer(name="Outro", phone="(11) 11111-1111")
        results = list_customers("88888")
        assert any(c.name == "Luiz" for c in results)

    def test_empty_search_returns_all(self):
        _make_customer(name="Tiago")
        results = list_customers("")
        assert len(results) >= 1


class TestDeleteCustomer:
    def test_delete_removes_customer(self):
        c = _make_customer(name="Para Deletar")
        delete_customer(c.id)
        customers = list_customers()
        assert not any(x.id == c.id for x in customers)

    def test_delete_nonexistent_is_noop(self):
        """Deletar ID inexistente não deve lançar exceção."""
        delete_customer(99999)  # should not raise
