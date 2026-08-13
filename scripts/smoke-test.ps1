# SEO-GEO MVP 冒烟测试
# 用法:
#   .\scripts\smoke-test.ps1                    # 默认 API=http://127.0.0.1:8000  SITE=http://127.0.0.1:3000
#   .\scripts\smoke-test.ps1 -ApiBase http://localhost -SiteBase http://localhost

param(
    [string]$ApiBase = "http://127.0.0.1:8000",
    [string]$SiteBase = "http://127.0.0.1:3000"
)

$ErrorActionPreference = "Stop"
$passed = 0
$failed = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [string]$Body = $null,
        [hashtable]$Headers = @{}
    )
    try {
        $params = @{
            Uri             = $Url
            Method          = $Method
            UseBasicParsing = $true
        }
        if ($Body) {
            $params.Body = $Body
            $params.ContentType = "application/json"
        }
        if ($Headers.Count -gt 0) {
            $params.Headers = $Headers
        }
        $r = Invoke-WebRequest @params
        if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 300) {
            Write-Host "[PASS] $Name ($($r.StatusCode))" -ForegroundColor Green
            $script:passed++
            return $r
        }
        Write-Host "[FAIL] $Name (HTTP $($r.StatusCode))" -ForegroundColor Red
        $script:failed++
        return $null
    }
    catch {
        Write-Host "[FAIL] $Name - $($_.Exception.Message)" -ForegroundColor Red
        $script:failed++
        return $null
    }
}

Write-Host "=== SEO-GEO 冒烟测试 ===" -ForegroundColor Cyan
Write-Host "API:  $ApiBase"
Write-Host "Site: $SiteBase"
Write-Host ""

# --- 后端 ---
Test-Endpoint "health" "$ApiBase/health"
Test-Endpoint "articles list" "$ApiBase/api/v1/articles"
Test-Endpoint "article detail" "$ApiBase/api/v1/articles/guangzhou-fangdao-men-guide"
Test-Endpoint "public lead" "$ApiBase/api/v1/leads" -Method POST -Body '{"name":"冒烟","phone":"13800138002","city":"广州","interest":"门窗"}'

$tokenResp = Test-Endpoint "auth token" "$ApiBase/api/v1/auth/token" -Method POST -Body "username=admin&password=admin123" -Headers @{"Content-Type"="application/x-www-form-urlencoded"}
$token = $null
if ($tokenResp) {
    $token = ($tokenResp.Content | ConvertFrom-Json).access_token
}

if ($token) {
    $auth = @{ Authorization = "Bearer $token" }
    Test-Endpoint "intents" "$ApiBase/api/v1/intents" -Method POST -Body '{"search_terms":["门窗"],"cities":["广州"],"top_k":5}' -Headers $auth
    $genResp = Test-Endpoint "content generate" "$ApiBase/api/v1/content/generate" -Method POST -Body '{"intent":"防盗门","city":"广州","type":"seo","priority":"P0","use_cache":false}' -Headers $auth
    if ($genResp) {
        $cid = ($genResp.Content | ConvertFrom-Json).content_id
        Test-Endpoint "eeat score" "$ApiBase/api/v1/content/eeat-score" -Method POST -Body "{`"content_id`":$cid,`"markdown`":`"# test`"}" -Headers $auth
        Test-Endpoint "publish" "$ApiBase/api/v1/publish" -Method POST -Body "{`"content_id`":$cid,`"target`":`"website`"}" -Headers $auth
        Test-Endpoint "content detail" "$ApiBase/api/v1/content/$cid" -Headers $auth
    }
    Test-Endpoint "metrics" "$ApiBase/api/v1/metrics?city=广州" -Headers $auth
    Test-Endpoint "leads list" "$ApiBase/api/v1/leads" -Headers $auth
}

# --- 前端 ---
$pages = @("/", "/guangzhou", "/shenzhen", "/beijing", "/articles", "/admin", "/sitemap.xml", "/robots.txt")
foreach ($p in $pages) {
    Test-Endpoint "page $p" "$SiteBase$p"
}

Write-Host ""
Write-Host "=== 结果: $passed 通过, $failed 失败 ===" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })
if ($failed -gt 0) { exit 1 }
