"""Unit tests for multi-language audit and patching (Python, C, C++, Java)."""

from docudoctor.languages import (
    Language,
    audit_code_by_language,
    patch_code_by_language,
)


def test_c_audit_and_patch():
    c_code = """
int calculate_discount(double price, double percent) {
    return price * (1.0 - percent / 100.0);
}

void print_greeting(const char* name) {
    printf("Hello %s", name);
}
"""
    result = audit_code_by_language(c_code, Language.C)
    assert result.total_functions == 2
    assert result.documented_functions == 0
    assert len(result.issues) == 2
    assert result.issues[0].issue_type == "Missing Docstring"

    # Patch C code
    patched, count = patch_code_by_language(c_code, Language.C)
    assert count == 2
    assert "@brief Calculate discount" in patched
    assert "@param price" in patched
    assert "@return int" in patched
    assert "@brief Print greeting" in patched

    # Re-audit patched C code
    re_audit = audit_code_by_language(patched, Language.C)
    assert re_audit.documented_functions == 2
    assert re_audit.score >= 90.0


def test_cpp_audit_and_patch():
    cpp_code = """
class PaymentGateway {
    double process(double amount) {
        return amount * 1.05;
    }
};

void send_notification(std::string user_id) {
    // send
}
"""
    result = audit_code_by_language(cpp_code, Language.CPP)
    assert result.total_classes == 1
    assert result.total_functions == 2
    assert result.documented_functions == 0

    # Patch C++ code
    patched, count = patch_code_by_language(cpp_code, Language.CPP)
    assert count == 3  # 1 class + 2 methods/functions
    assert "@brief PaymentGateway" in patched
    assert "@brief Process" in patched

    re_audit = audit_code_by_language(patched, Language.CPP)
    assert re_audit.documented_functions == 2
    assert re_audit.total_classes == 1
    assert re_audit.score >= 90.0


def test_java_audit_and_patch():
    java_code = """
public class InvoiceService {
    public double calculateTotal(double subtotal, double taxRate) {
        return subtotal * (1 + taxRate);
    }

    private void logEvent(String event) {
        System.out.println(event);
    }
}
"""
    result = audit_code_by_language(java_code, Language.JAVA)
    assert result.total_classes == 1
    assert result.total_functions == 2
    assert result.documented_functions == 0

    # Patch Java code
    patched, count = patch_code_by_language(java_code, Language.JAVA)
    assert count == 3
    assert "/**" in patched
    assert "* InvoiceService representation." in patched
    assert "* @param subtotal" in patched
    assert "* @return the computed double result" in patched

    re_audit = audit_code_by_language(patched, Language.JAVA)
    assert re_audit.documented_functions == 2
    assert re_audit.score >= 90.0


def test_language_detection_from_filename():
    assert Language.from_filename("app.py") == Language.PYTHON
    assert Language.from_filename("utils.c") == Language.C
    assert Language.from_filename("header.h") == Language.C
    assert Language.from_filename("server.cpp") == Language.CPP
    assert Language.from_filename("model.hpp") == Language.CPP
    assert Language.from_filename("Main.java") == Language.JAVA
