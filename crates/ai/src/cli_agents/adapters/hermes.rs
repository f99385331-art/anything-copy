//! Hermes Agent (`hermes -z`).
//!
//! Hermes declares `-z/--oneshot` with `metavar="PROMPT"`, taking the prompt as its value.
//! Model `-m` and custom args come before `-z <prompt>`.

use super::*;

pub struct Hermes;

impl AgentAdapter for Hermes {
    fn ids(&self) -> &'static [&'static str] {
        &["hermes"]
    }

    fn args(&self, cx: &ArgsCx) -> Vec<String> {
        let mut v = Vec::new();
        if let Some(m) = &cx.options.cli_model {
            v.extend(["-m".into(), m.clone()]);
        }
        v.extend(cx.options.args.iter().cloned());
        v.extend(["-z".into(), format!("{}{}", cx.preamble, cx.prompt)]);
        v
    }

    fn required_flags(&self) -> (&'static [&'static str], &'static [&'static str]) {
        (&["--help"], &["--oneshot"])
    }

    /// Plain `hermes <prompt>` opens the interactive session; a failed flag check keeps this adapter.
    fn plain_fallback(&self) -> bool {
        false
    }

    /// The `-z` runner sees nothing of a turn until it ends, can't be cancelled half-way, and
    /// carries the whole task book in argv. ACP carries the message in a session instead:
    /// progress streams, cancel asks, approvals arrive as cards, and a long message never
    /// touches Windows' command-line wall. `args()` above stays for the shape `verify_flags`
    /// checked and for a future `--oneshot` fallback; requires_acp makes run_cli refuse it.
    fn requires_acp(&self) -> bool {
        true
    }

    /// Session options measured against the real `hermes acp` (2026-11-12): `model` takes
    /// `provider:model` and `reasoning_effort` a level name — the startup line accepts neither
    /// (`hermes acp -h` has no `-m`), so the person's choices land on the session, not argv.
    /// An unknown bare model name is refused visibly by the agent, never quietly ignored.
    fn acp_session_config(&self, options: &BackendOptions) -> Vec<(String, String)> {
        let mut v = Vec::new();
        if let Some(m) = &options.cli_model {
            v.push(("model".to_string(), m.clone()));
        }
        if let Some(e) = options.effort {
            v.push(("reasoning_effort".to_string(), e.as_str().to_string()));
        }
        v
    }

    fn streams_json(&self) -> bool {
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn args(builder: bool, options: &BackendOptions) -> Vec<String> {
        let mcp = McpCommand { command: "craft-anything-cli".into(), args: vec!["mcp".into()], notes: None };
        Hermes.args(&ArgsCx { options, prompt: "make a game", preamble: "PRE ", mcp: &mcp, resume: None, builder, reads_checked: false, question: false })
    }

    #[test]
    fn the_prompt_goes_to_oneshot_after_the_flags() {
        assert_eq!(args(false, &BackendOptions::default()), ["-z", "PRE make a game"]);
        let options = BackendOptions { cli_model: Some("custom/qwen-2.5-coder".into()), args: vec!["-t".into(), "0.2".into()], ..Default::default() };
        assert_eq!(args(true, &options), ["-m", "custom/qwen-2.5-coder", "-t", "0.2", "-z", "PRE make a game"]);
        assert!(AgentAdapters::built_in().for_agent("hermes").ids().contains(&"hermes"), "registered, not the plain adapter");
        assert_eq!(Hermes.required_flags(), (&["--help"][..], &["--oneshot"][..]));
        assert!(!Hermes.plain_fallback());
    }

    #[test]
    fn the_builder_conversation_goes_over_acp_with_session_config() {
        assert!(Hermes.requires_acp(), "progress, cancel and approvals ride the session, not a silent -z");
        let o = BackendOptions { cli_model: Some("alibaba-token-plan-cn:qwen3.8-flash".into()), ..Default::default() };
        assert_eq!(
            Hermes.acp_session_config(&o),
            vec![("model".to_string(), "alibaba-token-plan-cn:qwen3.8-flash".to_string())],
            "the option ids measured against the real agent on 2026-11-12"
        );
        let with_effort = BackendOptions { effort: Some(crate::model::Effort::High), ..Default::default() };
        assert!(
            Hermes.acp_session_config(&with_effort).iter().any(|(k, v)| k == "reasoning_effort" && v == "high"),
            "effort lands as the level name the agent's own panel lists"
        );
        assert!(Hermes.acp_session_config(&BackendOptions::default()).is_empty(), "nothing set sends nothing");
    }
}
