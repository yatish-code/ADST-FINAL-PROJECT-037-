"""News mood: teaches a small model to read financial headlines.

Training data: Financial PhraseBank, ~4,800 sentences labelled positive, neutral or
negative by finance experts "from an investor's point of view".
Method: count word patterns (TF-IDF), then fit logistic regression. It trains in about a second.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline

from . import datasets


class NewsMood:
    def __init__(self):
        news = datasets.load_news()
        self.model = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
            LogisticRegression(max_iter=1000, C=5, class_weight="balanced"))

        self.accuracy = round(float(cross_val_score(self.model, news["text"], news["label"], cv=5).mean()) * 100)
        self.model.fit(news["text"], news["label"])
        self.sentences = len(news)

        picks = [news[news["label"] == label].sample(2, random_state=3)["text"].tolist()
                 for label in ("positive", "negative", "neutral")]
        self.examples = [text for group in picks for text in group]

    def score(self, headlines):
        """Score a list of headlines. Mood runs from -100 (very negative) to +100 (very positive)."""
        probabilities = self.model.predict_proba(headlines)
        classes = list(self.model.classes_)
        results = []
        for text, p in zip(headlines, probabilities):
            chances = dict(zip(classes, p))
            label = max(chances, key=chances.get)
            results.append(dict(text=text, label=label, confidence=round(chances[label] * 100),
                                mood=round((chances["positive"] - chances["negative"]) * 100)))
        average = round(sum(r["mood"] for r in results) / len(results)) if results else 0
        return dict(results=results, average_mood=average)
