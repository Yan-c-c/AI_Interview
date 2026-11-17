export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  last_login_at?: string;
}

export interface AuthSession {
  token: string;
  user: AuthUser;
}

export interface ChatMessage {
  id: string;
  role: string;
  text: string;
  createdAt: string;
}

export interface HistoryRecord {
  id: string;
  title: string;
  intent: string;
  agent: string;
  userMessage: string;
  assistantMessage: string;
  resultText: string;
  rawJson: string;
  createdAt: string;
}

export interface AssistantPayload {
  success: boolean;
  intent: string;
  agent: string;
  message: string;
  displayText: string;
  rawJson: string;
}

export class AgentShortcut {
  key: string;
  title: string;
  subtitle: string;
  icon: string;
  colors: string[];
  prompt: string;

  constructor(key: string, title: string, subtitle: string, icon: string, colors: string[], prompt: string) {
    this.key = key;
    this.title = title;
    this.subtitle = subtitle;
    this.icon = icon;
    this.colors = colors;
    this.prompt = prompt;
  }
}

export const AGENT_SHORTCUTS: AgentShortcut[] = [
  new AgentShortcut(
    'resume',
    '简历评估',
    '粘贴简历文本，生成优化建议',
    '简',
    ['#2979FF', '#ECF5FF'],
    '请帮我评估这份简历，指出岗位匹配度、主要风险、可量化优化建议和改写方向。\n\n目标岗位：\n\n简历文本：\n'
  ),
  new AgentShortcut(
    'interview',
    '模拟面试',
    '岗位、技能、项目驱动问答',
    '面',
    ['#19BE6B', '#F0F9EB'],
    '请基于以下岗位、技能栈和项目经历生成个性化面试题，并开始文字模拟面试。\n\n目标岗位：\n技能栈：\n项目经历：\n希望面试难度：\n'
  ),
  new AgentShortcut(
    'cover',
    '求职信',
    '公司、岗位、JD 生成正文',
    '信',
    ['#606266', '#F4F4F5'],
    '请生成一封个性化求职信，包含正式版和邮件精简版。\n\n目标公司：\n目标岗位：\n招聘 JD：\n个人背景：\n希望风格：\n'
  ),
  new AgentShortcut(
    'career',
    '职业规划',
    '背景、目标、困惑形成路径',
    '规',
    ['#2B85E4', '#ECF5FF'],
    '请为我生成职业规划，包含能力画像、目标岗位匹配、学习路径、项目补强和投递策略。\n\n当前背景：\n目标方向：\n当前困惑：\n可投入时间：\n期望城市/行业：\n'
  ),
  new AgentShortcut(
    'salary',
    '谈薪助手',
    'Offer、城市、经验谈判策略',
    '薪',
    ['#F29100', '#FDF6EC'],
    '请作为谈薪助手，根据以下信息生成薪资判断、谈判策略和 HR 话术。\n\n岗位：\n城市：\n工作年限：\n技能栈：\n当前 Offer：\n期望薪资：\n其他约束：\n'
  ),
  new AgentShortcut(
    'email',
    '邮件润色',
    '只生成或润色邮件正文',
    '邮',
    ['#82848A', '#F4F4F5'],
    '请帮我生成或润色求职邮件正文，只输出邮件主题、正文和可替换版本，不要执行发送。\n\n目标公司：\n目标岗位：\n收件人：\n原邮件/想表达的内容：\n个人背景：\n希望语气：\n'
  )
];

export function nowText(): string {
  const date = new Date();
  const yyyy = date.getFullYear();
  const mm = `${date.getMonth() + 1}`.padStart(2, '0');
  const dd = `${date.getDate()}`.padStart(2, '0');
  const hh = `${date.getHours()}`.padStart(2, '0');
  const mi = `${date.getMinutes()}`.padStart(2, '0');
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`;
}

export function makeId(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
}

export function intentLabel(intent: string): string {
  switch (intent) {
    case 'resume_evaluation':
      return '简历';
    case 'interview_question_generation':
      return '面试';
    case 'interview_audio_analysis':
      return '对话分析';
    case 'cover_letter_generation':
      return '求职信';
    case 'career_planning':
      return '规划';
    case 'salary_negotiation':
      return '谈薪';
    case 'general_chat':
      return '对话';
    default:
      return '记录';
  }
}
