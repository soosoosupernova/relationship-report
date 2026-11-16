#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""관계 패턴 리포트 v6(수정본) 검증 — QuickJS + 미니 DOM.

- 보상형 광고 게이트 6개 흐름(정상·무응답·닫기·오류·예외·SDK 없음/폴백)
- 잠금 상태 유료 본문 비노출, 타임아웃 폴백, 재생 중 버튼 잠금
- 퀴즈 흐름·극단 응답·topItem 4점 분기·동점 처리
- 메타/OG/접근성/안전장치 정적 점검
"""
import json
import re
import sys

import quickjs

SRC = "/workspace/work/relationship-report/index.html"
html = open(SRC, encoding="utf-8").read()
script = html[html.index("<script>") + 8: html.rindex("</script>")]

STUB = r"""
const __els = {};
function El(id, tag) {
  this.id = id; this.tag = tag || 'div'; this._cls = new Set(); this._html = '';
  this.textContent = ''; this.disabled = false; this.style = {}; this.onclick = null;
  this.dataset = {}; this._attrs = {}; this._children = []; this._focus = 0;
  const self = this;
  this.classList = {
    add: (c) => self._cls.add(c),
    remove: (c) => self._cls.delete(c),
    contains: (c) => self._cls.has(c),
    toggle: (c) => self._cls.has(c) ? self._cls.delete(c) : self._cls.add(c)
  };
  Object.defineProperty(this, 'innerHTML', {
    get: () => self._html,
    set: (v) => {
      self._html = String(v);
      self._children = [];
      const re = /<button[^>]*data-v="(\d+)"[^>]*>/g;
      let m;
      while ((m = re.exec(self._html)) !== null) {
        const b = new El(null, 'button');
        b.dataset.v = m[1];
        self._children.push(b);
      }
    }
  });
  this.setAttribute = (k, v) => { self._attrs[k] = String(v); };
  this.getAttribute = (k) => (k in self._attrs ? self._attrs[k] : null);
  this.querySelectorAll = (sel) => (sel === 'button' ? self._children : []);
  this.focus = () => { self._focus++; globalThis.__focused = self.id === null ? 'option' : self.id; };
  this.scrollIntoView = () => { globalThis.__scrolledTo = self.id; };
  this.querySelector = () => null;
}
['landing','quiz','result'].forEach(id => { __els['#' + id] = new El(id, 'section'); });
__els['#landing']._cls.add('active');
['qcount','dimlabel','progress','progressbar','qtext','options','freecontent','paidcontent',
 'unlock','adstatus','restart','print','start','prev','next','reporttitle'].forEach(id => {
  __els['#' + id] = new El(id, 'button');
});
globalThis.document = {
  querySelector: (sel) => {
    if (!__els[sel]) throw new Error('missing selector ' + sel);
    return __els[sel];
  },
  querySelectorAll: (sel) => sel === '.screen' ? [__els['#landing'], __els['#quiz'], __els['#result']] : []
};
globalThis.window = { scrollTo: () => {}, print: () => { globalThis.__printed = (globalThis.__printed || 0) + 1; } };
globalThis.__scrolledTo = null; globalThis.__printed = 0; globalThis.__focused = null;
const __timers = {}; let __tid = 1;
globalThis.setTimeout = (fn, ms) => { const id = __tid++; __timers[id] = fn; return id; };
globalThis.clearTimeout = (id) => { delete __timers[id]; };
globalThis.__fireTimers = () => { const ids = Object.keys(__timers); ids.forEach(i => { const fn = __timers[i]; delete __timers[i]; fn(); }); return ids.length; };
globalThis.__pendingTimers = () => Object.keys(__timers).length;
"""

TEST = r"""
function snap() {
  return JSON.stringify({
    unlockText: __els['#unlock'].textContent,
    unlockDisabled: __els['#unlock'].disabled,
    status: __els['#adstatus'].textContent,
    paidOpen: __els['#paidcontent'].classList.contains('open'),
    paidLen: __els['#paidcontent'].innerHTML.length,
    restartDisabled: __els['#restart'].disabled,
    printDisabled: __els['#print'].disabled,
    timers: __pendingTimers(),
    activeScreen: ['landing','quiz','result'].filter(s => __els['#' + s].classList.contains('active'))[0] || null,
    freeLen: __els['#freecontent'].innerHTML.length
  });
}
function quizThrough(answers) {
  __els['#start'].onclick();
  for (let i = 0; i < 16; i++) {
    const btns = __els['#options'].querySelectorAll('button');
    btns[answers[i] - 1].onclick();
    __els['#next'].onclick();
  }
  return JSON.parse(snap());
}
function reset() { __els['#restart'].onclick(); }
const out = { checks: [], flows: {} };
function chk(name, cond, detail) {
  out.checks.push({ name: name, pass: !!cond, detail: String(detail === undefined ? '' : detail) });
}

// ---------- 0. 초기 상태
out.flows.initial = JSON.parse(snap());
chk('초기: 버튼 활성', __els['#unlock'].disabled === false);
chk('초기: 유료 영역 닫힘', __els['#paidcontent'].classList.contains('open') === false);
chk('초기: 유료 본문 DOM에 없음', __els['#paidcontent'].innerHTML.length === 0, __els['#paidcontent'].innerHTML.length);

// ---------- 1. 결과 화면 진입(잠금 상태) — 유료 본문 미생성
const s1 = quizThrough(Array(16).fill(3));
out.flows.resultLocked = s1;
chk('퀴즈: 결과 화면 전환', s1.activeScreen === 'result', s1.activeScreen);
chk('퀴즈: 무료 결과 생성', s1.freeLen > 1500, s1.freeLen);
chk('[핵심] 잠금 상태에서 유료 본문 DOM 0자', s1.paidLen === 0, s1.paidLen);
chk('결과 화면 제목으로 포커스 이동', globalThis.__focused === 'reporttitle', globalThis.__focused);

// ---------- 2. SDK 미연결 → 무료 바로 열기 폴백
__els['#unlock'].onclick();
out.flows.noBridge = JSON.parse(snap());
chk('SDK 없음: 방문자용 안내', __els['#adstatus'].textContent.indexOf('지금은 광고가 준비되지 않아 전체 리포트를 바로 열어드릴게요') === 0, __els['#adstatus'].textContent);
chk('SDK 없음: 잠금 해제(폴백)', __els['#paidcontent'].classList.contains('open') === true);
chk('SDK 없음: 유료 본문 생성됨', __els['#paidcontent'].innerHTML.length > 3000, __els['#paidcontent'].innerHTML.length);
chk('SDK 없음: 버튼 문구', __els['#unlock'].textContent === '전체 리포트가 열렸습니다', __els['#unlock'].textContent);
chk('SDK 없음: 버튼 비활성', __els['#unlock'].disabled === true);
chk('SDK 없음: 본문으로 스크롤', globalThis.__scrolledTo === 'paidcontent', globalThis.__scrolledTo);

// ---------- 3. 다시 응답하기 → 유료 본문 제거·잠금 복구
const paidHtml1 = __els['#paidcontent'].innerHTML;
reset();
out.flows.afterRestart = JSON.parse(snap());
chk('다시 응답하기: 랜딩 복귀', __els['#landing'].classList.contains('active'));
chk('다시 응답하기: 유료 본문 제거', __els['#paidcontent'].innerHTML.length === 0);
chk('다시 응답하기: 버튼 문구/활성 복구', __els['#unlock'].textContent === '광고 보고 열기' && __els['#unlock'].disabled === false);
chk('다시 응답하기: 안내 문구 복구', __els['#adstatus'].textContent.indexOf('광고 시청이 완료되면') === 0);
chk('다시 응답하기: 인쇄·재응답 버튼 활성', __els['#print'].disabled === false && __els['#restart'].disabled === false);

// ---------- 4. SDK가 콜백을 전혀 주지 않음(무응답) → 10초 타임아웃 폴백
quizThrough(Array(16).fill(3));
let called = 0;
globalThis.window.RelationshipReportAds = { showRewardedAd: function (o) { called++; globalThis.__opts = o; } };
__els['#unlock'].onclick();
out.flows.noCallback = JSON.parse(snap());
chk('SDK 무응답: 요청 1회 전달', called === 1, called);
chk('SDK 무응답: 로딩 문구', __els['#unlock'].textContent === '광고 불러오는 중…', __els['#unlock'].textContent);
chk('SDK 무응답: 버튼 일시 비활성', __els['#unlock'].disabled === true);
chk('SDK 무응답: 재생 중 다시 응답하기 비활성', __els['#restart'].disabled === true);
chk('SDK 무응답: 재생 중 인쇄 비활성', __els['#print'].disabled === true);
__els['#unlock'].onclick();
chk('재생 중 중복 클릭 차단', called === 1, called);
const beforeTimeout = __els['#paidcontent'].innerHTML.length;
chk('재생 중에는 유료 본문 미생성', beforeTimeout === 0, beforeTimeout);
chk('타임아웃 타이머 등록', __pendingTimers() === 1, __pendingTimers());
__fireTimers();
out.flows.timeout = JSON.parse(snap());
chk('10초 타임아웃: 폴백 안내', __els['#adstatus'].textContent.indexOf('광고가 제때 응답하지 않아') === 0, __els['#adstatus'].textContent);
chk('10초 타임아웃: 잠금 해제', __els['#paidcontent'].classList.contains('open') === true);
chk('10초 타임아웃: 버튼 잠금 해제 상태 정리', __els['#unlock'].textContent === '전체 리포트가 열렸습니다');
chk('10초 타임아웃: 다시 응답하기 복구', __els['#restart'].disabled === false);
chk('타임아웃 후 남은 타이머 없음', __pendingTimers() === 0, __pendingTimers());
// 늦게 도착한 콜백이 화면을 되돌리지 않는지
try { globalThis.__opts.onClosed(); } catch (e) {}
chk('타임아웃 뒤 늦은 onClosed 무시', __els['#paidcontent'].classList.contains('open') === true && __els['#adstatus'].textContent.indexOf('광고가 제때') === 0);

// ---------- 5. 중도 닫기(보상 없음) → 잠금 유지
reset();
quizThrough(Array(16).fill(3));
let saved = null;
globalThis.window.RelationshipReportAds = { showRewardedAd: function (o) { saved = o; } };
__els['#unlock'].onclick();
saved.onClosed();
out.flows.closedNoReward = JSON.parse(snap());
chk('중도 닫기: 잠금 유지', __els['#paidcontent'].classList.contains('open') === false);
chk('중도 닫기: 유료 본문 여전히 없음', __els['#paidcontent'].innerHTML.length === 0);
chk('중도 닫기: 안내 문구', __els['#adstatus'].textContent.indexOf('광고 시청이 완료되지 않아') === 0, __els['#adstatus'].textContent);
chk('중도 닫기: 버튼 복구', __els['#unlock'].textContent === '광고 보고 열기' && __els['#unlock'].disabled === false);
chk('중도 닫기: 인쇄·재응답 복구', __els['#print'].disabled === false && __els['#restart'].disabled === false);
chk('중도 닫기: 타이머 정리', __pendingTimers() === 0, __pendingTimers());

// ---------- 6. 보상 후 닫힘
__els['#unlock'].onclick();
saved.onRewarded();
saved.onClosed();
out.flows.rewarded = JSON.parse(snap());
chk('보상: 잠금 해제', __els['#paidcontent'].classList.contains('open') === true);
chk('보상: 버튼 문구', __els['#unlock'].textContent === '전체 리포트가 열렸습니다');
chk('보상: 안내 문구', __els['#adstatus'].textContent.indexOf('광고 시청이 확인되어') === 0, __els['#adstatus'].textContent);
chk('보상: 본문으로 스크롤', globalThis.__scrolledTo === 'paidcontent');
chk('보상 뒤 onClosed가 문구를 덮지 않음', __els['#adstatus'].textContent.indexOf('완료되지 않아') === -1);
chk('보상: 유료 본문 4개 섹션', (__els['#paidcontent'].innerHTML.match(/<section class="card">/g) || []).length === 4);

// ---------- 7. 오류(no-fill) → 폴백
reset();
quizThrough(Array(16).fill(3));
globalThis.window.RelationshipReportAds = { showRewardedAd: function (o) { globalThis.__o2 = o; } };
__els['#unlock'].onclick();
globalThis.__o2.onError();
out.flows.onError = JSON.parse(snap());
chk('오류: 폴백으로 잠금 해제', __els['#paidcontent'].classList.contains('open') === true);
chk('오류: 방문자용 안내', __els['#adstatus'].textContent.indexOf('지금은 광고를 불러올 수 없어 전체 리포트를 바로 열어드릴게요') === 0, __els['#adstatus'].textContent);

// ---------- 8. 브리지가 예외를 던짐 → 폴백
reset();
quizThrough(Array(16).fill(3));
globalThis.window.RelationshipReportAds = { showRewardedAd: function () { throw new Error('boom'); } };
__els['#unlock'].onclick();
out.flows.throwing = JSON.parse(snap());
chk('예외: 폴백으로 잠금 해제', __els['#paidcontent'].classList.contains('open') === true);
chk('예외: 안내 문구', __els['#adstatus'].textContent.indexOf('지금은 광고를 불러올 수 없어') === 0);

// ---------- 9. 재생 중 '다시 응답하기' 직접 호출 차단
reset();
quizThrough(Array(16).fill(3));
let asked = 0;
globalThis.window.RelationshipReportAds = { showRewardedAd: function () { asked++; } };
__els['#unlock'].onclick();
const statusDuring = __els['#adstatus'].textContent;
__els['#restart'].onclick();
chk('재생 중 다시 응답하기: 화면 그대로', __els['#result'].classList.contains('active') && __els['#adstatus'].textContent === statusDuring);
__els['#print'].onclick();
chk('재생 중 인쇄: window.print 미호출', globalThis.__printed === 0, globalThis.__printed);
__fireTimers();  // 무응답 타임아웃 종료

// ---------- 10. 응답 없이 인쇄 (정상 상태)
chk('타임아웃 폴백 뒤 잠금 해제', __els['#paidcontent'].classList.contains('open') === true);
reset();
chk('리셋 후 인쇄 버튼은 정상 동작', (function () { __els['#print'].onclick(); return globalThis.__printed === 1; })(), globalThis.__printed);

// ---------- 11. 극단 응답
function render(answers) {
  reset();
  const s = quizThrough(answers);
  __els['#unlock'].onclick();
  __fireTimers();  // 브리지 무응답 → 타임아웃 폴백으로 본문 생성
  return { free: __els['#freecontent'].innerHTML, paid: __els['#paidcontent'].innerHTML, snap: s };
}
const cases = {
  allLow: Array(16).fill(1),
  allMid: Array(16).fill(3),
  allHigh: Array(16).fill(5),
  anxHigh: [5,5,5,5, 1,1,1,1, 1,1,1,1, 1,1,1,1],
  avoHigh: [1,1,1,1, 5,5,5,5, 1,1,1,1, 1,1,1,1],
  mix: [5,4,2,1, 1,3,5,2, 4,1,5,2, 3,5,1,2]
};
let bad = [];
out.flows.cases = {};
for (const k in cases) {
  const r = render(cases[k]);
  if (/NaN|undefined|\[object/.test(r.free + r.paid)) bad.push(k);
  out.flows.cases[k] = r.paid.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').slice(0, 260);
}
chk('모든 응답에서 NaN/undefined 없음', bad.length === 0, bad.join(','));

// ---------- 12. topItem 4점 분기
const lowAll = render(Array(16).fill(1)).paid.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
chk('[수정] 전부 1점: "가장 높게" 단정 없음', lowAll.indexOf('가장 높게 응답한 문항') === -1);
chk('[수정] 전부 1점: 두드러진 문항 없음 안내', lowAll.indexOf('4점 이상으로 높게 응답한 문항이 없어서') >= 0);
chk('[수정] 전부 1점: 조율 문장 미부착', lowAll.indexOf('조율하려는 행동을 활용할 수 있어요') === -1);
const allFive = render(Array(16).fill(5)).paid.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
chk('[수정] 전부 5점: 동점 안내 문구', allFive.indexOf('함께 높게 응답한 문항') >= 0);
chk('5점: 해석 문장 부착', allFive.indexOf('관계의 거리감으로 연결해 읽을 수 있어요') >= 0);
const one = render([5,1,1,1, 1,1,1,1, 1,1,1,5, 1,1,1,1]).paid.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
chk('단일 최고점: "가장 높게" 문구', one.indexOf('가장 높게 응답한 문항') >= 0);

// ---------- 13. 퀴즈 UI 상태
reset();
chk('UI 테스트 진입: 광고 세션 종료됨', __pendingTimers() === 0, __pendingTimers());
__els['#start'].onclick();
chk('1번 문항: 다음 비활성', __els['#next'].disabled === true);
chk('1번 문항: 진행 표시', __els['#qcount'].textContent === '01 / 16', __els['#qcount'].textContent);
chk('1번 문항: 차원 라벨', __els['#dimlabel'].textContent === '애착불안');
chk('진행바 aria-valuenow 갱신', __els['#progressbar'].getAttribute('aria-valuenow') === '1', __els['#progressbar'].getAttribute('aria-valuenow'));
const ob = __els['#options'].querySelectorAll('button');
chk('옵션 5개', ob.length === 5, ob.length);
chk('옵션 aria-pressed 초기값', __els['#options'].innerHTML.indexOf('aria-pressed="false"') >= 0);
ob[2].onclick();
chk('응답 후 다음 활성', __els['#next'].disabled === false);
chk('선택 표시(aria-pressed)', __els['#options'].innerHTML.indexOf('aria-pressed="true"') >= 0);
chk('선택 시 체크 표시', __els['#options'].innerHTML.indexOf('\u2713') >= 0);
chk('선택 후 포커스 유지', globalThis.__focused === 'option', globalThis.__focused);
__els['#next'].onclick();
chk('2번 문항 다음 비활성', __els['#next'].disabled === true);
__els['#prev'].onclick();
chk('1번 복귀 시 응답 유지', __els['#next'].disabled === false && __els['#options'].innerHTML.indexOf('aria-pressed="true"') >= 0);

// ---------- 14. 잠금 상태 인쇄 시 유료 본문 미출력 확인용 상태
reset();
quizThrough(Array(16).fill(2));
chk('잠금 상태: 인쇄해도 유료 본문 없음', __els['#paidcontent'].innerHTML.length === 0);

JSON.stringify(out);
"""

ctx = quickjs.Context()
try:
    ctx.eval(STUB)
    ctx.eval(script)
    result = json.loads(ctx.eval(TEST))
except Exception as e:  # noqa
    print("EXEC FAIL:", e)
    sys.exit(1)

for c in result["checks"]:
    print(("[PASS] " if c["pass"] else "[FAIL] ") + c["name"] + ("" if c["pass"] else "  -> " + c["detail"]))

print("\n---- flows ----")
for k, v in result["flows"].items():
    print(k, "=", json.dumps(v, ensure_ascii=False)[:300])

n = len(result["checks"])
p = sum(1 for c in result["checks"] if c["pass"])
print("\n%d/%d" % (p, n))
sys.exit(0 if p == n else 2)
