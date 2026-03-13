// Mock AI response scenarios for demo
var MOCK_SCENARIOS = {
  default: {
    plan: [
      'TodoList 컴포넌트에서 현재 필터 상태를 관리할 state 추가',
      'FilterBar 컴포넌트 생성 (All / Active / Completed)',
      '필터 조건에 따라 todo 목록 필터링하는 로직 구현',
      'FilterBar에 활성 필터 하이라이트 스타일 적용',
      '필터 변경 시 URL 해시 업데이트 (히스토리 지원)',
    ],
    response: [
      { type: 'heading', text: '분석 결과' },
      { type: 'text', text: '현재 TodoList 컴포넌트를 확인했습니다. 필터 기능을 추가하겠습니다.' },
      { type: 'code', lang: 'jsx', text: '// FilterBar.jsx\nconst FilterBar = ({ current, onChange }) => {\n  const filters = [\'all\', \'active\', \'completed\'];\n  return (\n    <div className="filter-bar">\n      {filters.map(f => (\n        <button\n          key={f}\n          className={current === f ? \'active\' : \'\'}\n          onClick={() => onChange(f)}\n        >\n          {f.charAt(0).toUpperCase() + f.slice(1)}\n        </button>\n      ))}\n    </div>\n  );\n};' },
      { type: 'text', text: 'TodoList에 필터 state를 추가합니다:' },
      { type: 'code', lang: 'jsx', text: 'const [filter, setFilter] = useState(\'all\');\n\nconst filteredTodos = todos.filter(todo => {\n  if (filter === \'active\') return !todo.completed;\n  if (filter === \'completed\') return todo.completed;\n  return true;\n});' },
      { type: 'text', text: '이렇게 하면 3개 탭으로 todo를 필터링할 수 있습니다.' }
    ]
  }
};

var GENERIC_RESPONSE = [
  { type: 'heading', text: '실행 결과' },
  { type: 'code', lang: 'js', text: '// 요청에 따른 구현 결과\nfunction handle() {\n  console.log("처리 완료");\n  return { status: "success" };\n}' },
  { type: 'text', text: '작업이 완료되었습니다. 추가 수정이 필요하면 셀을 재실행하세요.' }
];

function getMockResponse(prompt) {
  var p = prompt.toLowerCase();
  if (p.indexOf('필터') !== -1 || p.indexOf('filter') !== -1 || p.indexOf('todo') !== -1 || p.indexOf('투두') !== -1) {
    return MOCK_SCENARIOS.default;
  }
  return {
    plan: [
      '요청 분석 및 컨텍스트 파악',
      '관련 파일 탐색 및 의존성 확인',
      '구현 코드 작성',
      '테스트 및 검증',
    ],
    response: [
      { type: 'heading', text: '실행 결과' },
      { type: 'text', text: '프롬프트를 분석했습니다: "' + prompt + '"' },
      GENERIC_RESPONSE[1],
      GENERIC_RESPONSE[2]
    ]
  };
}
