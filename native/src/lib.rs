//! CPU-heavy document loops. No filesystem access or Python calls while detached.

use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::fmt::Write;

fn encode_rtf(text: &str) -> String {
    let mut output = String::with_capacity(text.len() + 32);
    output.push_str("{\\rtf1\\ansi\\deff0\n");
    // RTF uses signed UTF-16 units, including both halves of emoji/surrogates.
    for unit in text.encode_utf16() {
        match unit {
            92 => output.push_str("\\\\"),
            123 => output.push_str("\\{"),
            125 => output.push_str("\\}"),
            10 => output.push_str("\\par\n"),
            0..=127 => output.push(char::from(unit as u8)),
            _ => write!(output, "\\u{}?", unit as i16).unwrap(),
        }
    }
    output.push_str("\n}\n");
    output
}

fn decode_pdf_literal(data: &[u8]) -> Vec<u8> {
    let mut output = Vec::with_capacity(data.len());
    let mut i = 0;
    while i < data.len() {
        let byte = data[i];
        i += 1;
        if byte != b'\\' {
            output.push(byte);
            continue;
        }
        if i == data.len() {
            break;
        }
        let escaped = data[i];
        i += 1;
        match escaped {
            b'n' => output.push(b'\n'),
            b'r' => output.push(b'\r'),
            b't' => output.push(b'\t'),
            b'b' => output.push(8),
            b'f' => output.push(12),
            b'\r' => {
                if data.get(i) == Some(&b'\n') {
                    i += 1;
                }
            }
            b'\n' => (),
            b'0'..=b'7' => {
                let mut value = (escaped - b'0') as u16;
                for _ in 0..2 {
                    if i < data.len() && (b'0'..=b'7').contains(&data[i]) {
                        value = value * 8 + (data[i] - b'0') as u16;
                        i += 1;
                    } else {
                        break;
                    }
                }
                output.push(value as u8);
            }
            _ => output.push(escaped),
        }
    }
    output
}

#[pyfunction]
fn to_rtf(py: Python<'_>, text: String) -> String {
    py.detach(|| encode_rtf(&text))
}

#[pyfunction]
fn unescape_pdf_literal<'py>(py: Python<'py>, data: &[u8]) -> Bound<'py, PyBytes> {
    let output = py.detach(|| decode_pdf_literal(data));
    PyBytes::new(py, &output)
}

#[pymodule]
fn media_converter_native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(to_rtf, module)?)?;
    module.add_function(wrap_pyfunction!(unescape_pdf_literal, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rtf_uses_utf16_surrogate_pairs() {
        assert_eq!(encode_rtf("🦀"), "{\\rtf1\\ansi\\deff0\n\\u-10178?\\u-8832?\n}\n");
        assert!(encode_rtf("{\\}\n").contains("\\{\\\\\\}\\par\n"));
    }

    #[test]
    fn pdf_escapes_continuations_and_octal() {
        assert_eq!(decode_pdf_literal(b"a\\n\\(b\\)\\\\\\777\\12x"), b"a\n(b)\\\xff\nx");
        assert_eq!(decode_pdf_literal(b"a\\\r\nb\\\nc\\"), b"abc");
        assert_eq!(decode_pdf_literal(b"\\z\\8"), b"z8");
    }
}
