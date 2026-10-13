import type { InterviewQuestionReport as Report, MockInterviewScenario } from "@/lib/api/interviewQuestion";

const positions = ["Java 后端", "大模型", "数据分析", "前端", "测试开发"];
const difficulties: MockInterviewScenario["difficulty"][] = ["基础", "中等", "进阶"];
const modes: MockInterviewScenario["mode"][] = ["技术一面", "项目深挖", "HR 面", "压力面", "综合模拟"];
const questionCountOptions = [3, 5, 8, 10];

const sceneCategoryMap: Record<string, string[]> = {
  "技术一面": ["技术基础题", "技术进阶题", "项目深挖题"],
  "项目深挖": ["项目深挖题", "场景设计题", "技术进阶题"],
  "HR 面": ["项目深挖题", "场景设计题", "技术基础题"],
  "压力面": ["技术进阶题", "场景设计题", "项目深挖题"],
  "综合模拟": ["项目深挖题", "技术基础题", "技术进阶题", "场景设计题"],
};

function difficultyRank(value: string) {
  if (value === "easy") return 1;
  if (value === "medium") return 2;
  if (value === "hard") return 3;
  return 2;
}

function targetDifficulty(value: string) {
  if (value === "基础") return 1;
  if (value === "进阶") return 3;
  return 2;
}

function flattenQuestions(report: Report) {
  return report.questions?.length ? report.questions : Object.values(report.question_sets || {}).flat();
}

export function pickQuestions(report: Report, scenario: MockInterviewScenario, count: number) {
  const nonFollowUpQuestions = flattenQuestions(report).filter((question) => question.category !== "追问题");
  const all = nonFollowUpQuestions.length ? nonFollowUpQuestions : flattenQuestions(report);
  const categories = sceneCategoryMap[scenario.mode] || sceneCategoryMap["综合模拟"];
  const target = targetDifficulty(scenario.difficulty);
  const sorted = [...all].sort((a, b) => {
    const categoryA = categories.includes(a.category) ? 0 : 1;
    const categoryB = categories.includes(b.category) ? 0 : 1;
    const difficultyA = Math.abs(difficultyRank(a.difficulty) - target);
    const difficultyB = Math.abs(difficultyRank(b.difficulty) - target);
    return categoryA - categoryB || difficultyA - difficultyB;
  });
  return sorted.slice(0, count);
}

