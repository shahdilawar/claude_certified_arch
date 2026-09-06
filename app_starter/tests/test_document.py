import os
import shutil
import stat
import pytest
from markitdown import MarkItDownException
from tools.document import binary_document_to_markdown, document_path_to_markdown


class TestBinaryDocumentToMarkdown:
    # Define fixture paths
    FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
    DOCX_FIXTURE = os.path.join(FIXTURES_DIR, "mcp_docs.docx")
    PDF_FIXTURE = os.path.join(FIXTURES_DIR, "mcp_docs.pdf")

    def test_fixture_files_exist(self):
        """Verify test fixtures exist."""
        assert os.path.exists(self.DOCX_FIXTURE), (
            f"DOCX fixture not found at {self.DOCX_FIXTURE}"
        )
        assert os.path.exists(self.PDF_FIXTURE), (
            f"PDF fixture not found at {self.PDF_FIXTURE}"
        )

    def test_binary_document_to_markdown_with_docx(self):
        """Test converting a DOCX document to markdown."""
        # Read binary content from the fixture
        with open(self.DOCX_FIXTURE, "rb") as f:
            docx_data = f.read()

        # Call function
        result = binary_document_to_markdown(docx_data, "docx")

        # Basic assertions to check the conversion was successful
        assert isinstance(result, str)
        assert len(result) > 0
        # Check for typical markdown formatting - this will depend on your actual test file
        assert "#" in result or "-" in result or "*" in result

    def test_binary_document_to_markdown_with_pdf(self):
        """Test converting a PDF document to markdown."""
        # Read binary content from the fixture
        with open(self.PDF_FIXTURE, "rb") as f:
            pdf_data = f.read()

        # Call function
        result = binary_document_to_markdown(pdf_data, "pdf")

        # Basic assertions to check the conversion was successful
        assert isinstance(result, str)
        assert len(result) > 0
        # Check for typical markdown formatting - this will depend on your actual test file
        assert "#" in result or "-" in result or "*" in result


class TestDocumentPathToMarkdown:
    # Define fixture paths
    FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
    DOCX_FIXTURE = os.path.join(FIXTURES_DIR, "mcp_docs.docx")
    PDF_FIXTURE = os.path.join(FIXTURES_DIR, "mcp_docs.pdf")

    def test_document_path_to_markdown_with_pdf(self):
        """Test converting a PDF document to markdown by path."""
        result = document_path_to_markdown(self.PDF_FIXTURE)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "#" in result or "-" in result or "*" in result

    def test_document_path_to_markdown_with_docx(self):
        """Test converting a DOCX document to markdown by path."""
        result = document_path_to_markdown(self.DOCX_FIXTURE)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "#" in result or "-" in result or "*" in result

    def test_document_path_to_markdown_matches_binary_conversion(self):
        """Reading by path should produce the same output as converting the same bytes directly."""
        with open(self.PDF_FIXTURE, "rb") as f:
            pdf_data = f.read()
        expected = binary_document_to_markdown(pdf_data, "pdf")

        actual = document_path_to_markdown(self.PDF_FIXTURE)

        assert actual == expected

    def test_document_path_to_markdown_with_relative_path(self):
        """Relative paths should resolve the same as absolute ones."""
        relative_path = os.path.relpath(self.PDF_FIXTURE)

        result = document_path_to_markdown(relative_path)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_nonexistent_path_raises_file_not_found(self):
        """A path that doesn't exist should raise a clear, specific error."""
        missing_path = os.path.join(self.FIXTURES_DIR, "does_not_exist.pdf")

        with pytest.raises(FileNotFoundError):
            document_path_to_markdown(missing_path)

    def test_directory_path_raises_error(self):
        """Pointing at a directory instead of a file should raise a clear error."""
        with pytest.raises(IsADirectoryError):
            document_path_to_markdown(self.FIXTURES_DIR)

    def test_path_without_extension_raises_error(self, tmp_path):
        """A path with no file extension can't be mapped to a document type."""
        target = tmp_path / "myfile"
        target.write_bytes(b"content")

        with pytest.raises(ValueError):
            document_path_to_markdown(str(target))

    def test_unicode_and_spaces_in_filename(self, tmp_path):
        """Filenames with spaces and non-ASCII characters should work."""
        target = tmp_path / "my report café.pdf"
        shutil.copyfile(self.PDF_FIXTURE, target)

        result = document_path_to_markdown(str(target))

        assert isinstance(result, str)
        assert len(result) > 0

    def test_uppercase_extension_is_handled(self, tmp_path):
        """Extension matching should be case-insensitive."""
        target = tmp_path / "UPPER.PDF"
        shutil.copyfile(self.PDF_FIXTURE, target)

        result = document_path_to_markdown(str(target))

        assert isinstance(result, str)
        assert len(result) > 0

    def test_zero_byte_file_raises_error(self, tmp_path):
        """An empty file can't be converted and shouldn't silently succeed."""
        target = tmp_path / "empty.pdf"
        target.write_bytes(b"")

        with pytest.raises(MarkItDownException):
            document_path_to_markdown(str(target))

    def test_corrupted_file_raises_error(self, tmp_path):
        """Non-text garbage bytes with a document extension should fail conversion clearly."""
        target = tmp_path / "corrupted.pdf"
        # Invalid UTF-8, non-PDF binary noise: markitdown falls back to
        # plain-text on decodable content, so this must not be decodable.
        target.write_bytes(bytes([0xFF, 0xD8, 0x00, 0x01, 0x02, 0x80, 0x81, 0xFE]) * 20)

        with pytest.raises(MarkItDownException):
            document_path_to_markdown(str(target))

    def test_unreadable_file_raises_permission_error(self, tmp_path):
        """A file without read permission should raise a clear permission error."""
        target = tmp_path / "no_permission.pdf"
        shutil.copyfile(self.PDF_FIXTURE, target)
        target.chmod(0)

        try:
            with pytest.raises(PermissionError):
                document_path_to_markdown(str(target))
        finally:
            target.chmod(stat.S_IRWXU)
