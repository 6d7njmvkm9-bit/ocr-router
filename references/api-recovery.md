# API 运行与失败恢复

任务状态：queued -> processing -> done / failed / timed_out

错误分类：auth_failed / rate_limited / network_error / timeout / file_too_large / unsupported_format / bad_result / partial_result

失败后切换候选后端，认证失败不重复撞同一凭证。
