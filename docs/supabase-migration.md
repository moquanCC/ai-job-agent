# Supabase 云端迁移设计

## 迁移目标与边界

Supabase 版本用于多用户登录、跨设备同步和云端岗位/分析历史。当前 SQLite 后端继续保留，作为离线演示、测试和无网络降级路径。迁移在独立分支 `agent/supabase-cloud` 实施，不直接修改稳定 `main`。

第一阶段只迁移结构化数据和认证，不上传完整简历原文。简历文件进入 Storage 前必须增加明确同意、保留期限和一键删除验证。

## 后端接口

现有 `AnalysisService` 只依赖以下存储行为；云端实现应保持相同语义：

```python
class JobStore(Protocol):
    def upsert_many(self, jobs: list[JobProfile]) -> int: ...
    def list_jobs(self) -> list[JobProfile]: ...
    def get(self, job_id: str) -> JobProfile | None: ...

class AnalysisStore(Protocol):
    def save(self, candidate_id: str, job_id: str, payload: dict) -> int: ...
    def delete_candidate(self, candidate_id: str) -> int: ...
```

通过 `STORAGE_BACKEND=sqlite|supabase` 选择实现，默认仍为 `sqlite`。

## 数据模型

| 表 | 关键字段 | 所有权 | 保留策略 |
|---|---|---|---|
| `profiles` | `user_id uuid PK`, `display_name`, `created_at` | 当前登录用户 | 删除账号时级联删除 |
| `jobs` | `job_id text PK`, `company`, `title`, `location`, `payload jsonb` | 系统公共岗位库 | 管理员维护；用户只读 |
| `analyses` | `id uuid PK`, `user_id`, `candidate_id`, `job_id`, `payload jsonb` | 当前登录用户 | 用户可单条/全部删除 |
| `resume_files` | `id uuid PK`, `user_id`, `storage_path`, `expires_at` | 当前登录用户 | 默认 30 天自动清理 |

`candidate_id` 不是授权依据；所有授权必须使用 `user_id = auth.uid()`。

## RLS 基线

所有 `public` 表启用 RLS。用户数据策略必须同时验证角色与所有权：

```sql
alter table public.analyses enable row level security;

create policy "users read own analyses"
on public.analyses for select
to authenticated
using ((select auth.uid()) = user_id);

create policy "users insert own analyses"
on public.analyses for insert
to authenticated
with check ((select auth.uid()) = user_id);

create policy "users update own analyses"
on public.analyses for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

create policy "users delete own analyses"
on public.analyses for delete
to authenticated
using ((select auth.uid()) = user_id);
```

`profiles` 和 `resume_files` 使用同样的所有权模式。`jobs` 对 `authenticated` 仅开放 `SELECT`；导入和修改必须通过服务器侧管理流程完成。

禁止事项：

- 不使用 `user_metadata` 做授权；角色数据应位于 `app_metadata`。
- 不把 `service_role` 或 secret key 放入 Streamlit 前端或提交到 Git。
- 不以 `TO authenticated` 代替行所有权判断。
- UPDATE 策略不能缺少 `WITH CHECK`。
- 不为绕过权限错误随意添加 `SECURITY DEFINER`。

## Storage

Bucket `resumes` 设为私有，路径固定为 `{auth.uid()}/{resume_id}/{filename}`。上传、读取、更新和删除策略均检查首段目录与 `auth.uid()` 相同。文件替换需要 INSERT、SELECT、UPDATE 三类策略。

客户端只能使用 publishable key。服务端机密仅存在于部署平台的加密环境变量中。

## 分阶段验证

1. 在本地 Supabase 环境创建 schema 和 RLS，使用两个测试账号验证互相不可见。
2. 对每张用户表测试 SELECT、INSERT、UPDATE、DELETE 的允许与拒绝路径。
3. 执行 Supabase database advisors，解决安全与性能提示。
4. 运行现有 21 项测试，并为两个存储后端增加相同契约测试。
5. 验证“删除我的数据”同时删除分析行和 Storage 对象。
6. 只有在 RLS、删除和回退路径全部通过后，才连接公开部署。

## 分支计划

```text
main                         稳定 SQLite Demo
└── agent/supabase-cloud     Auth、Postgres、RLS、Storage 与契约测试
```

首个云端里程碑只包含登录、岗位只读、个人分析历史和删除功能。pgvector 与简历文件上传放在后续里程碑，避免一次引入过多隐私和检索变量。
