# Fine-tuning vs retrieval

A useful shorthand is:

- **Fine-tuning changes behavior.** Teach task conventions, taxonomy, output format, domain style,
  tool-selection patterns, or when to abstain.
- **Retrieval supplies current evidence.** Contracts, policies, regulations, account data, and other
  changing authoritative facts belong in retrievable systems of record.

## Relation to classic utterance training

Training an Azure Language/CLU-style intent model from labeled utterances is conceptually related:
you provide supervised examples so a model learns a task boundary. The target is usually narrow,
such as `utterance -> intent + entities`.

Chat-model supervised fine-tuning uses richer training examples—typically a conversation containing
system/user messages and the desired assistant response. Instead of only learning an intent class,
the model can learn extraction structure, response conventions, classification taxonomies, or tool
calling behavior.

Do not use fine-tuning as a substitute for current legal authority or the actual contract being
reviewed. Those should remain retrieved evidence.
