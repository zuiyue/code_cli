explore_subagent = {
    "name": "explore",
    "description": (
        "Fast subagent for exploring codebases. "
        "Use for file search, code reading, and understanding project structure. "
        "Cannot execute bash commands or write files."
    ),
    "system_prompt": (
        "You are a code exploration specialist. "
        "Your job is to quickly find and read relevant files. "
        "Use ls, glob, grep, and read_file to explore the codebase. "
        "Report back what you find concisely."
    ),
}

general_subagent = {
    "name": "general",
    "description": (
        "General-purpose subagent for complex multi-step tasks. "
        "Has access to all tools including bash execution."
    ),
    "system_prompt": (
        "You are a general-purpose assistant for complex tasks. "
        "Break down the problem, use available tools, and deliver results."
    ),
}
