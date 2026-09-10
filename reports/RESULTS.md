# Current results

The current controlled comparison is summarized in `final_comparison.json`. The strongest reliable finding so far is the ablation between raw DeepSeek and DeepSeek with contract protection: pass rate increased from 86.0% to 100.0%, and the corrected mean score increased from 0.8835 to 0.9675.

Rule Router and the current Bandit scaffold are identical in this version because the Bandit has not yet been given a stochastic exploration policy or enough online reward updates. They should not be presented as evidence that reinforcement learning has already improved over rules.

