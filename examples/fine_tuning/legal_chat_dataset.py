from enterprise_ai_patterns.fine_tuning.dataset import ChatExample, ChatTurn, write_jsonl

examples = [
    ChatExample((
        ChatTurn("system", "Classify contract clauses using the approved legal taxonomy."),
        ChatTurn("user", "Either party may terminate this Agreement on thirty days written notice."),
        ChatTurn("assistant", '{"clause_type":"termination_for_convenience"}'),
    )),
    ChatExample((
        ChatTurn("system", "Classify contract clauses using the approved legal taxonomy."),
        ChatTurn("user", "Neither party shall be liable for indirect or consequential damages."),
        ChatTurn("assistant", '{"clause_type":"limitation_of_liability"}'),
    )),
]

write_jsonl(examples, "legal_chat_examples.jsonl")
