import unittest
from io import BytesIO

import pandas as pd

from frontend_utils import find_review_column, parse_reviews, rating_summary, read_review_file


class ParseReviewsTests(unittest.TestCase):
    def test_parse_reviews_splits_non_empty_lines(self):
        text = "Great service\nBad packaging\n\nFast delivery"
        self.assertEqual(parse_reviews(text), ["Great service", "Bad packaging", "Fast delivery"])

    def test_parse_reviews_returns_empty_for_blank_input(self):
        self.assertEqual(parse_reviews("\n  \n"), [])

    def test_csv_upload_and_review_column_detection(self):
        records = read_review_file(b"Review,customer\nGreat service,Ana\n", "reviews.csv")
        self.assertEqual(records[0]["Review"], "Great service")
        self.assertEqual(find_review_column(records[0].keys()), "Review")

    def test_xlsx_upload(self):
        source = BytesIO()
        pd.DataFrame({"feedback": ["Fast delivery"]}).to_excel(source, index=False)
        records = read_review_file(source.getvalue(), "reviews.xlsx")
        self.assertEqual(records, [{"feedback": "Fast delivery"}])

    def test_rating_summary(self):
        summary = rating_summary([{"rating": 5}, {"score": 3}, {"rating": 4}])
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["average"], 4)
        self.assertAlmostEqual(summary["positive_percentage"], 66.666, places=2)


if __name__ == "__main__":
    unittest.main()
