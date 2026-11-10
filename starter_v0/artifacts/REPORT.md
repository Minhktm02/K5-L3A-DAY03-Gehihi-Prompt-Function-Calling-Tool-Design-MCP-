# Day 03 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. **Xong trước 16:30** để làm tài liệu phụ trợ khi demo. Có thể làm thành poster HTML/SVG (`artifacts/poster.html` / `poster.svg`) để show cho team cùng zone.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. **Có thể hoàn thiện sau buổi debate để nộp bài.**

## Team

- Team: [fill in team name]
- Members: [fill in names]
- Provider/model: OpenRouter / `openai/gpt-4o-mini`

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research Agent tìm tin trên web và bài đăng mạng xã hội, đọc URL do người dùng cung cấp, rồi trình bày kết quả thành digest có nguồn. Agent cũng có thể tra cứu chính sách nội bộ, tìm bài arXiv và issue/PR công khai trên GitHub; trước khi gửi nội dung lên Telegram, cần hỏi xác nhận.

**Link dùng thử (deploy):**

Chưa có public demo URL được ghi nhận. Chạy local từ `starter_v0` bằng `python chat.py --provider openrouter --version v3`.

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| `clarify` | Hỏi người dùng để lấy thông tin còn thiếu hoặc xác nhận hành động. | Không |
| `timeline` | Lấy bài đăng gần đây từ một tài khoản X. | Không |
| `social_search` | Tìm bài đăng X theo từ khóa, mới nhất hoặc phổ biến. | Không |
| `lookup` | Tìm thông tin web, gồm tin tức theo khoảng thời gian. | Không |
| `fetch` | Đọc nội dung của một URL cụ thể. | Không |
| `format` | Biến các kết quả đã thu thập thành digest Markdown. | Không |
| `send` | Gửi nội dung lên Telegram sau khi người dùng xác nhận. | Không |
| `policy` | Tìm trong tài liệu chính sách nội bộ cục bộ. | Không |
| `papers` | Tìm bài nghiên cứu trên arXiv. | Không |
| `paper_text` | Trích xuất văn bản từ bài arXiv. | Không |
| `github_search` | Tìm issue và pull request công khai trên GitHub. | Có |

## A3. Câu hỏi mẫu để thử

1. `Tin AI hôm nay có gì nổi bật?`
2. `Tweet mới nhất của Sam Altman là gì?`
3. `Tóm tắt bài viết này hộ mình: https://anthropic.com/news/claude`
4. `Search GitHub issues for pandas nullable dtype bug.`
5. `Gửi nội dung sau lên Telegram: Demo starts at 4:30.` Khi agent hỏi xác nhận, trả lời **No** để không gửi thật.

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version Evidence

Metrics below are from the canonical v0-v3 base runs. Accuracy fields are fractions of 20 cases.

| Version | Changed Artifact / Hypothesis | Case Accuracy | Tool Routing | Arguments | Multi-turn | Run File |
|---|---|---:|---:|---:|---:|---|
| v0 | Baseline; establish failure patterns. | 0.65 (13/20) | 0.75 | 0.65 | 1.00 | `runs/v0_B_base_openrouter_20261110T104359482508.json` |
| v1 | `artifacts/tools.yaml`; clarify that news intent belongs in `topic=news`, not in the query text. | 0.75 (15/20) | 0.75 | 0.75 | 1.00 | `runs/v1_B_base_openrouter_20261110T110852948495.json` |
| v2 | `artifacts/tools.yaml`; make `send` Telegram-only and require confirmation. | 0.80 (16/20) | 0.80 | 0.80 | 1.00 | `runs/v2_B_base_openrouter_20261110T111450814846.json` |
| v3 | `artifacts/system_prompt.md`; replace the conflicting immediate-send instruction with a yes/no confirmation step. | 0.90 (18/20) | 0.90 | 0.90 | 1.00 | `runs/v3_B_base_openrouter_20261110T111913681025.json` |

Note: a later run labeled v1 (`runs/v1_B_base_openrouter_20261110T113153362437.json`) has the same prompt and tool hashes as v3 and also scores 0.90; it is a rerun of the v3 artifacts, not the canonical v1 comparison.

## B2. Failure Analysis

| Case ID / Run | Failure Type | Actual Tool Calls | What Failed | Response |
|---|---|---|---|---|
| R03 / v0 | `wrong_tool` (actual mismatch: wrong argument) | `lookup(query="AI news", topic="news", timeframe="day")` | Correct tool and topic, but query differed from expected `AI`. | Clarified query/topic separation in the lookup description; passed in v1. |
| R12 / v2 | `wrong_boundary` | `send(text="Bản tin này")` | Called send instead of asking the user to confirm first. | Replaced the system prompt's immediate-send instruction; the v3 base case passed and live chat asked for confirmation. |
| R10 / v3 | `missing_info` | `timeline(screenname="sama")` | Guessed an account instead of asking whose tweets to summarize. | Still unresolved; next improvement should remove the prompt's guess-when-missing instruction and route to `clarify`. |
| R11 / v3 | `missing_info` | `fetch(url="https://example.com/article")` | Invented a URL instead of asking the user to provide the article link. | Still unresolved; next improvement should require a real user-provided URL before calling `fetch`. |

## B3. Team Eval Cases

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| G01 | Normalize `@karpathy` and retain limit 3. | `timeline(screenname="karpathy", limit=3)` | Not run; no group run JSON. |
| G02 | Latest X posts about AI safety. | `social_search(query="AI safety", search_type="Latest")` | Not run; no group run JSON. |
| G03 | Route GitHub issue searches to the team-added tool. | `github_search(query="pandas nullable dtype bug")` | Not run; no group run JSON. |
| G04 | Do not call tools for a simple acknowledgment. | No tool | Not run; no group run JSON. |
| G05 | Ask for the user's account handle instead of guessing. | `clarify(response_type="text")` | Not run; no group run JSON. |
| G06 | Correct the timeframe to this month and retain AI news. | `lookup(query="AI", topic="news", timeframe="month")` | Not run; no group run JSON. |
| G07 | Replace Top with Latest after a correction. | `social_search(query="OpenAI", search_type="Latest")` | Not run; no group run JSON. |
| G08 | Switch from web news to social search and keep the topic. | `social_search(query="OpenAI")` | Not run; no group run JSON. |
| G09 | Respect a rejection of a pending Telegram send. | No tool | Not run; no group run JSON. |
| G10 | Refine the query and retain news/week filters. | `lookup(query="offshore wind", topic="news", timeframe="week")` | Not run; no group run JSON. |

## B4. Live Chat Evidence

| Turn | User Request | Tool Calls | Version Evidence | Outcome |
|---|---|---|---|---|
| 1 | `Tin AI hôm nay có gì nổi bật?` | `lookup(query="AI", topic="news", timeframe="day")` | v3 prompt hash; OpenRouter `openai/gpt-4o-mini`. | Answered with five web-news items and links. |
| 2 | `Tóm tắt 5 tweet mới nhất giúp mình` | `timeline(screenname="sama", limit=5)`, then `format` | Same transcript. | Produced a digest, but guessed Sam Altman without asking. This is a live example of the remaining missing-info failure. |
| 3 | `Gửi nội dung sau lên Telegram: Demo starts at 4:30.` | `clarify(response_type="yes_no")` | Same transcript. | Correctly waited for confirmation; transcript ends in `waiting_for_user`. No Telegram send is recorded. |

## B5. Bonus Evidence

Only fill if your team did bonus.

| Bonus | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| GitHub issue search tool | `tools/github_search/`; `tests/test_tools_todo.py` | Mocked happy path, invalid input, and HTTP-error tests pass. | Uses the public GitHub API; rate limits and response changes remain possible. |
| Tool unit tests | `tests/test_tools_todo.py` | User-provided focused output: 17 passed, 0 skipped. | Full-suite output was not available for this report. All HTTP tests use mocks. |
| Telegram send | `tools/send/`; live transcript | Live chat asks for yes/no confirmation before any send. | Live transcript ends before the user's answer; no live send was tested. |
| UI / deploy | No public URL recorded | Not verified as deployed. | Do not share a public demo link until deployment is confirmed. |
| arXiv / company policy | `tools/papers/`, `tools/paper_text/`, `tools/policy/` | Tools are present in the declaration and registry. | No separate bonus run evidence recorded. |

Seventeen tool TODO tests are implemented, including three tests for the new `github_search` tool. The focused run found a mistaken assertion in the thread-format test, not a bug in the existing tool; the assertion was corrected and the subsequent focused output passed all 17 tests. No existing-tool regression bug is claimed.

## B6. Reflection

- **System prompt:** The immediate-send instruction conflicted with the intended confirmation boundary. Replacing it improved the base score from 0.80 to 0.90 and the live transcript shows `clarify` waiting for a yes/no answer.
- **Tool declarations:** The generic lookup description did not separate the search subject from the news topic; clarifying it coincided with the v0-to-v1 improvement from 0.65 to 0.75. The send description made its scope and confirmation requirement explicit.
- **Manual review:** `R10` and `R11` are safety/grounding failures: the model invents an account or URL. The live transcript independently confirms the missing-account behavior, which is more informative than the final score alone.
- **Next:** Add an explicit no-guess/ask-for-required-input routing rule, rerun the base suite, run the group suite, and capture the resulting logs. Confirm the UI and public demo link before the showdown.

## B7. Small Local Model Challenge (bonus)

Not run; no Ollama/local-model run JSON is present.

| Version | Model (provider) | Prompt/Tools | case_accuracy | tool_routing | argument | multiturn | Run File |
|---|---|---|---|---|---|---|---|
| v3 | OpenRouter / `openai/gpt-4o-mini` | v3 | 0.90 | 0.90 | 0.90 | 1.00 | `runs/v3_B_base_openrouter_20261110T111913681025.json` |
| v3-... | (ollama) | v3 |  |  |  |  |  |
| v3-... | (ollama) | v3 |  |  |  |  |  |
| v4-local |  |  |  |  |  |  |  |
| v5-local |  |  |  |  |  |  |  |

Lỗi đặc thù của model nhỏ (đếm từ run JSON):

| Failure Pattern | Count | Example Case | Fix Tried | Helped? |
|---|---|---|---|---|
| wrong / hallucinated tool |  |  |  |  |
| invalid JSON args (`_invalid_json_arguments`) |  |  |  |  |
| no tool call / answered directly |  |  |  |  |
| missed `clarify` |  |  |  |  |
| repeated / unnecessary calls |  |  |  |  |

- Cái gì giúp model nhỏ gọi tool đúng hơn nhất? Bằng chứng?
- Bản prompt tối ưu cho local chạy trên model cloud thì sao?
- Khi nào nhóm sẽ chọn model local thay vì cloud cho agent này?
