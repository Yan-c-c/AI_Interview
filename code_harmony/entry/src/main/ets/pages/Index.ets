import common from '@ohos.app.ability.common';
import { AGENT_SHORTCUTS, AgentShortcut, AssistantPayload, AuthUser, ChatMessage, HistoryRecord, intentLabel, makeId, nowText } from '../models/Models';
import { ApiClient } from '../services/ApiClient';
import { DEFAULT_BASE_URL, getBackendCandidateUrls, normalizeBaseUrl, StorageService } from '../services/StorageService';
import { AgentGradientCard, COLOR_BG, COLOR_LINE, COLOR_PANEL, COLOR_PRIMARY, COLOR_SUB, COLOR_TEXT, GlassBottomTab, TnLiteButton, TnLiteEmpty, TnLiteInput, TnLiteTag, TnLiteTextArea } from '../components/TnLiteControls';

@Entry
@Component
struct Index {
  @State private ready: boolean = false;
  @State private currentTab: number = 0;
  @State private authMode: number = 0;
  @State private loading: boolean = false;
  @State private user: AuthUser | undefined = undefined;
  @State private token: string = '';
  @State private baseUrl: string = DEFAULT_BASE_URL;
  @State private autoSaveHistory: boolean = true;
  @State private loginEmail: string = '';
  @State private loginPassword: string = '';
  @State private registerName: string = '';
  @State private registerEmail: string = '';
  @State private registerPassword: string = '';
  @State private draft: string = '';
  @State private sessionId: string = makeId('session');
  @State private messages: ChatMessage[] = [
    {
      id: makeId('msg'),
      role: 'assistant',
      text: '把简历、项目、岗位、面试回答或 Offer 信息贴进来，我会调用后端 Agent 处理。',
      createdAt: nowText()
    }
  ];
  @State private history: HistoryRecord[] = [];
  @State private selectedHistoryIndex: number = -1;
  private appContext: common.Context | undefined = undefined;

  aboutToAppear(): void {
    const hostContext = this.getUIContext().getHostContext();
    if (hostContext) {
      this.appContext = hostContext as common.Context;
    }
    this.bootstrap();
  }

  private async bootstrap(): Promise<void> {
    const context = this.appContext;
    if (!context) {
      this.ready = true;
      return;
    }
    this.baseUrl = await StorageService.getBaseUrl(context);
    this.autoSaveHistory = await StorageService.getAutoSave(context);
    this.history = await StorageService.getHistory(context);
    this.token = await StorageService.getToken(context);
    const cachedUser = await StorageService.getUser(context);
    if (cachedUser) {
      this.user = cachedUser;
    }
    await this.resolveBackend(false);
    if (this.token.length > 0) {
      await this.validateToken(false);
    }
    this.ready = true;
  }

  build() {
    Stack() {
      Column()
        .width('100%')
        .height('100%')
        .backgroundColor(COLOR_BG);

      if (!this.ready) {
        this.LoadingView();
      } else if (!this.user || this.token.length === 0) {
        this.AuthView();
      } else {
        this.MainView();
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(COLOR_BG);
  }

  @Builder
  private LoadingView() {
    Column({ space: 16 }) {
      LoadingProgress()
        .width(36)
        .height(36)
        .color(COLOR_PRIMARY);
      Text('正在校验登录状态')
        .fontSize(14)
        .fontColor(COLOR_SUB);
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center);
  }

  @Builder
  private AuthView() {
    Scroll() {
      Column({ space: 20 }) {
        this.BrandHeader();
        this.AuthCard();
      }
      .width('100%')
      .padding({ left: 20, right: 20, top: 54, bottom: 36 });
    }
    .width('100%')
    .height('100%');
  }

  @Builder
  private BrandHeader() {
    Column({ space: 10 }) {
      Text('AI')
        .fontSize(20)
        .fontWeight(FontWeight.Bold)
        .fontColor('#FFFFFF')
        .width(54)
        .height(54)
        .textAlign(TextAlign.Center)
        .backgroundColor(COLOR_PRIMARY)
        .borderRadius(12)
        .shadow({ radius: 8, color: '#2979FF20', offsetY: 3 });
      Text('智能面试助手')
        .fontSize(30)
        .fontWeight(FontWeight.Bold)
        .fontColor(COLOR_TEXT);
      Text('轻量用户版 · 文字对话驱动所有 Agent')
        .fontSize(14)
        .fontColor(COLOR_SUB);
    }
    .width('100%')
    .alignItems(HorizontalAlign.Start);
  }

  @Builder
  private AuthCard() {
    Column({ space: 16 }) {
      Row() {
        this.AuthSegment(0, '登录');
        this.AuthSegment(1, '注册');
      }
      .padding(4)
      .height(46)
      .width('100%')
      .backgroundColor(COLOR_BG)
      .borderRadius(999);

      if (this.authMode === 0) {
        TnLiteInput({ value: $loginEmail, placeholder: '邮箱' });
        TnLiteInput({ value: $loginPassword, placeholder: '密码', isPassword: true });
      } else {
        TnLiteInput({ value: $registerName, placeholder: '姓名' });
        TnLiteInput({ value: $registerEmail, placeholder: '邮箱' });
        TnLiteInput({ value: $registerPassword, placeholder: '密码', isPassword: true });
      }

      TnLiteButton({
        text: this.authMode === 0 ? '登录' : '注册并登录',
        icon: this.authMode === 0 ? '→' : '+',
        loading: this.loading,
        disabled: !this.canSubmitAuth(),
        onTap: () => this.submitAuth()
      });

      Text('Token 会保存在本地 Preferences，启动时自动校验登录状态。')
        .fontSize(12)
        .fontColor(COLOR_SUB)
        .lineHeight(18);
    }
    .width('100%')
    .padding(18)
    .backgroundColor(COLOR_PANEL)
    .borderRadius(14)
    .border({ width: 1, color: COLOR_LINE })
    .shadow({ radius: 8, color: '#00000008', offsetY: 3 });
  }

  @Builder
  private AuthSegment(index: number, title: string) {
    Text(title)
      .layoutWeight(1)
      .height('100%')
      .fontSize(14)
      .fontWeight(this.authMode === index ? FontWeight.Bold : FontWeight.Medium)
      .fontColor(this.authMode === index ? COLOR_PRIMARY : COLOR_SUB)
      .textAlign(TextAlign.Center)
      .backgroundColor(this.authMode === index ? COLOR_PANEL : Color.Transparent)
      .borderRadius(999)
      .shadow(this.authMode === index ? { radius: 6, color: '#00000008', offsetY: 2 } : { radius: 0, color: '#00000000', offsetY: 0 })
      .onClick(() => {
        this.authMode = index;
      });
  }

  @Builder
  private MainView() {
    Stack({ alignContent: Alignment.Bottom }) {
      Column() {
        if (this.currentTab === 0) {
          this.HomePage();
        } else if (this.currentTab === 1) {
          this.AssistantPage();
        } else if (this.currentTab === 2) {
          this.HistoryPage();
        } else {
          this.ProfilePage();
        }
      }
      .width('100%')
      .height('100%')
      .padding({ bottom: 76 });
      GlassBottomTab({ currentIndex: $currentTab });
    }
    .width('100%')
    .height('100%');
  }

  @Builder
  private HomePage() {
    Scroll() {
      Column({ space: 18 }) {
        this.TopHero();
        Row() {
          Text('Agent 快捷入口')
            .fontSize(20)
            .fontWeight(FontWeight.Bold)
            .fontColor(COLOR_TEXT);
          Blank();
          TnLiteTag({ text: '纯文字', color: COLOR_PRIMARY });
        }
        .width('100%');
        Flex({ wrap: FlexWrap.Wrap, justifyContent: FlexAlign.SpaceBetween }) {
          ForEach(AGENT_SHORTCUTS, (item: AgentShortcut) => {
            AgentGradientCard({
              item: item,
              onTap: (prompt: string) => this.openAgent(prompt)
            });
          }, (item: AgentShortcut) => item.key);
        }
        .width('100%');
        this.RecentPanel();
      }
      .padding({ left: 18, right: 18, top: 52, bottom: 18 })
      .width('100%');
    }
    .height('100%');
  }

  @Builder
  private TopHero() {
    Column({ space: 14 }) {
      Row() {
        Column({ space: 6 }) {
          Text(`你好，${this.user?.name ?? '同学'}`)
            .fontSize(26)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FFFFFF');
          Text('粘贴材料，后端 IntentRouter 会自动分发 Agent')
            .fontSize(13)
            .fontColor('#FFFFFFCC')
            .lineHeight(19);
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Start);
          Text('AI')
            .fontSize(15)
            .fontWeight(FontWeight.Bold)
            .fontColor(COLOR_PRIMARY)
            .padding({ left: 12, right: 12, top: 7, bottom: 7 })
            .backgroundColor('#FFFFFF')
            .borderRadius(999);
      }
      .width('100%');
      Row({ space: 8 }) {
        this.WhitePill('简历');
        this.WhitePill('面试');
        this.WhitePill('求职信');
        this.WhitePill('谈薪');
      }
      .width('100%');
    }
    .width('100%')
    .padding(20)
    .backgroundColor('#2B85E4')
    .borderRadius(16)
    .shadow({ radius: 8, color: '#2B85E420', offsetY: 4 });
  }

  @Builder
  private WhitePill(text: string) {
    Text(text)
      .fontSize(12)
      .fontWeight(FontWeight.Medium)
      .fontColor(COLOR_PRIMARY)
      .padding({ left: 10, right: 10, top: 5, bottom: 5 })
      .backgroundColor('#FFFFFF')
      .borderRadius(999);
  }

  @Builder
  private RecentPanel() {
    Column({ space: 12 }) {
      Row() {
        Text('最近生成')
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .fontColor(COLOR_TEXT);
        Blank();
        Text(`${this.history.length} 条`)
          .fontSize(12)
          .fontColor(COLOR_SUB);
      }
      .width('100%');
      if (this.history.length === 0) {
        TnLiteEmpty({ title: '暂无历史', description: '完成一次对话后，报告会自动保存在这里。', icon: '◷' });
      } else {
        ForEach(this.history.slice(0, 3), (item: HistoryRecord, index: number) => {
          this.HistoryRow(item, index);
        }, (item: HistoryRecord) => item.id);
      }
    }
    .width('100%')
    .padding(16)
    .backgroundColor(COLOR_PANEL)
    .borderRadius(14)
    .border({ width: 1, color: COLOR_LINE });
  }

  @Builder
  private AssistantPage() {
    Column() {
      Row() {
        Text('统一助手')
          .fontSize(24)
          .fontWeight(FontWeight.Bold)
          .fontColor(COLOR_TEXT);
        Blank();
        TnLiteButton({
          text: '新会话',
          icon: '+',
          plain: true,
          startColor: COLOR_PRIMARY,
          onTap: () => this.newChat()
        })
        .width(104);
      }
      .padding({ left: 18, right: 18, top: 52, bottom: 10 })
      .width('100%');

      Scroll() {
        Column({ space: 12 }) {
          ForEach(this.messages, (item: ChatMessage) => {
            this.MessageBubble(item);
          }, (item: ChatMessage) => item.id);
          if (this.loading) {
            Row({ space: 8 }) {
              LoadingProgress().width(18).height(18).color(COLOR_PRIMARY);
              Text('生成中')
                .fontSize(13)
                .fontColor(COLOR_SUB);
            }
            .width('100%')
            .padding({ left: 18, right: 18 });
          }
        }
        .padding({ left: 18, right: 18, top: 12, bottom: 12 })
        .width('100%');
      }
      .layoutWeight(1)
      .width('100%');

      Column({ space: 10 }) {
        TnLiteTextArea({ value: $draft, placeholder: '粘贴简历、项目经历、面试回答、Offer 信息或邮件正文...', minHeight: 112 });
        TnLiteButton({
          text: '发送给后端 Agent',
          icon: '↑',
          loading: this.loading,
          disabled: this.draft.trim().length === 0,
          onTap: () => this.sendMessage()
        });
      }
      .padding({ left: 18, right: 18, top: 12, bottom: 12 })
      .backgroundColor(COLOR_PANEL)
      .border({ width: { top: 1 }, color: COLOR_LINE });
    }
    .width('100%')
    .height('100%');
  }

  @Builder
  private MessageBubble(item: ChatMessage) {
    Row() {
      if (item.role === 'user') {
        Blank();
      }
      Column({ space: 8 }) {
        Text(item.text)
          .fontSize(14)
          .lineHeight(21)
          .fontColor(item.role === 'user' ? '#FFFFFF' : COLOR_TEXT)
          .textAlign(TextAlign.Start);
        Text(item.createdAt)
          .fontSize(10)
          .fontColor(item.role === 'user' ? '#FFFFFFAA' : COLOR_SUB);
      }
      .padding(14)
      .constraintSize({ maxWidth: '82%' })
      .backgroundColor(item.role === 'user' ? COLOR_PRIMARY : '#FFFFFF')
      .borderRadius(12)
      .border({ width: item.role === 'user' ? 0 : 1, color: item.role === 'user' ? COLOR_PRIMARY : COLOR_LINE })
      .shadow({ radius: item.role === 'user' ? 7 : 4, color: item.role === 'user' ? '#2979FF18' : '#00000006', offsetY: 2 });
      if (item.role !== 'user') {
        Blank();
      }
    }
    .width('100%');
  }

  @Builder
  private HistoryPage() {
    Scroll() {
      Column({ space: 14 }) {
        Text('历史记录')
          .fontSize(24)
          .fontWeight(FontWeight.Bold)
          .fontColor(COLOR_TEXT)
          .width('100%');
        if (this.history.length === 0) {
          TnLiteEmpty({ title: '暂无生成记录', description: '对话和报告会保存在本地，便于后续复盘。', icon: '◷' });
        } else {
          ForEach(this.history, (item: HistoryRecord, index: number) => {
            this.HistoryRow(item, index);
          }, (item: HistoryRecord) => item.id);
        }
        if (this.selectedHistoryIndex >= 0 && this.selectedHistoryIndex < this.history.length) {
          this.HistoryDetail(this.history[this.selectedHistoryIndex]);
        }
      }
      .padding({ left: 18, right: 18, top: 52, bottom: 18 })
      .width('100%');
    }
    .height('100%');
  }

  @Builder
  private HistoryRow(item: HistoryRecord, index: number) {
    Column({ space: 8 }) {
      Row() {
        TnLiteTag({ text: intentLabel(item.intent), color: COLOR_PRIMARY });
        Blank();
        Text(item.createdAt)
          .fontSize(11)
          .fontColor(COLOR_SUB);
      }
      .width('100%');
      Text(item.title)
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor(COLOR_TEXT)
        .maxLines(1)
        .textOverflow({ overflow: TextOverflow.Ellipsis });
      Text(item.resultText || item.assistantMessage)
        .fontSize(12)
        .lineHeight(18)
        .fontColor(COLOR_SUB)
        .maxLines(2)
        .textOverflow({ overflow: TextOverflow.Ellipsis });
    }
    .width('100%')
    .padding(14)
    .backgroundColor(this.selectedHistoryIndex === index ? '#ECF5FF' : COLOR_PANEL)
    .borderRadius(12)
    .border({ width: 1, color: this.selectedHistoryIndex === index ? '#A0CFFF' : COLOR_LINE })
    .onClick(() => {
      this.selectedHistoryIndex = this.selectedHistoryIndex === index ? -1 : index;
    });
  }

  @Builder
  private HistoryDetail(item: HistoryRecord) {
    Column({ space: 12 }) {
      Text('记录详情')
        .fontSize(18)
        .fontWeight(FontWeight.Bold)
        .fontColor(COLOR_TEXT)
        .width('100%');
      Text('输入')
        .fontSize(13)
        .fontWeight(FontWeight.Bold)
        .fontColor(COLOR_SUB)
        .width('100%');
      Text(item.userMessage)
        .fontSize(13)
        .lineHeight(20)
        .fontColor(COLOR_TEXT)
        .width('100%');
      Divider().color(COLOR_LINE);
      Text('结果')
        .fontSize(13)
        .fontWeight(FontWeight.Bold)
        .fontColor(COLOR_SUB)
        .width('100%');
      Text(item.resultText)
        .fontSize(13)
        .lineHeight(20)
        .fontColor(COLOR_TEXT)
        .width('100%');
    }
    .width('100%')
    .padding(16)
    .backgroundColor('#FFFFFF')
    .borderRadius(14)
    .border({ width: 1, color: COLOR_LINE });
  }

  @Builder
  private ProfilePage() {
    Scroll() {
      Column({ space: 16 }) {
        Text('我的')
          .fontSize(24)
          .fontWeight(FontWeight.Bold)
          .fontColor(COLOR_TEXT)
          .width('100%')
          .padding({ top: 52 });
        this.ProfileHeaderCard();
        Row({ space: 12 }) {
          this.MetricCard('历史记录', `${this.history.length}`, '本地保存');
          this.MetricCard('Token', this.token.length > 0 ? '已保存' : '未保存', 'Keychain/Preferences');
        }
        .width('100%');
        this.SettingCard();
      }
      .padding({ left: 18, right: 18, bottom: 18 })
      .width('100%');
    }
    .height('100%');
  }

  @Builder
  private ProfileHeaderCard() {
    Row({ space: 14 }) {
      Text(this.user?.name.substring(0, 1) ?? 'U')
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
        .fontColor('#FFFFFF')
        .width(58)
        .height(58)
        .textAlign(TextAlign.Center)
        .backgroundColor(COLOR_PRIMARY)
        .borderRadius(12);
      Column({ space: 5 }) {
        Row({ space: 8 }) {
          Text(this.user?.name ?? '用户')
            .fontSize(20)
            .fontWeight(FontWeight.Bold)
            .fontColor(COLOR_TEXT);
          TnLiteTag({ text: this.user?.status ?? 'active', color: '#15803D' });
        }
        .width('100%');
        Text(this.user?.email ?? '')
          .fontSize(13)
          .fontColor(COLOR_SUB)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
          .width('100%');
        Text(`角色：${this.user?.role ?? 'user'}`)
          .fontSize(12)
          .fontColor(COLOR_SUB)
          .width('100%');
      }
      .layoutWeight(1)
      .alignItems(HorizontalAlign.Start);
    }
    .width('100%')
    .padding(16)
    .backgroundColor(COLOR_PANEL)
    .borderRadius(14)
    .border({ width: 1, color: COLOR_LINE })
    .shadow({ radius: 6, color: '#00000008', offsetY: 2 });
  }

  @Builder
  private MetricCard(label: string, value: string, caption: string) {
    Column({ space: 6 }) {
      Text(label)
        .fontSize(12)
        .fontColor(COLOR_SUB)
        .width('100%');
      Text(value)
        .fontSize(value.length > 4 ? 17 : 22)
        .fontWeight(FontWeight.Bold)
        .fontColor(COLOR_TEXT)
        .width('100%');
      Text(caption)
        .fontSize(11)
        .fontColor(COLOR_SUB)
        .width('100%')
        .maxLines(1)
        .textOverflow({ overflow: TextOverflow.Ellipsis });
    }
    .layoutWeight(1)
    .padding(14)
    .backgroundColor(COLOR_PANEL)
    .borderRadius(12)
    .border({ width: 1, color: COLOR_LINE });
  }

  @Builder
  private SettingCard() {
    Column({ space: 14 }) {
      Text('偏好与安全')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor(COLOR_TEXT)
        .width('100%');
      Row() {
        Text('自动保存历史')
          .fontSize(15)
          .fontColor(COLOR_TEXT);
        Blank();
        Toggle({ type: ToggleType.Switch, isOn: this.autoSaveHistory })
          .selectedColor(COLOR_PRIMARY)
          .onChange((value: boolean) => {
            this.autoSaveHistory = value;
            this.saveAutoSave();
          });
      }
      .width('100%');
      Divider().color(COLOR_LINE);
      this.InfoRow('账号状态', this.user?.status ?? 'active');
      this.InfoRow('角色', this.user?.role ?? 'user');
      TnLiteButton({
        text: '校验登录',
        icon: '✓',
        plain: true,
        startColor: COLOR_PRIMARY,
        loading: this.loading,
        onTap: () => this.validateToken(true)
      });
      TnLiteButton({
        text: '退出登录',
        icon: '↩',
        startColor: '#DD6161',
        endColor: '#DD6161',
        onTap: () => this.logout()
      });
    }
    .width('100%')
    .padding(16)
    .backgroundColor(COLOR_PANEL)
    .borderRadius(14)
    .border({ width: 1, color: COLOR_LINE });
  }

  @Builder
  private InfoRow(label: string, value: string) {
    Row() {
      Text(label)
        .fontSize(14)
        .fontColor(COLOR_SUB);
      Blank();
      Text(value)
        .fontSize(14)
        .fontWeight(FontWeight.Medium)
        .fontColor(COLOR_TEXT);
    }
    .width('100%');
  }

  private canSubmitAuth(): boolean {
    if (this.loading) {
      return false;
    }
    if (this.authMode === 0) {
      return this.loginEmail.includes('@') && this.loginPassword.length >= 6;
    }
    return this.registerName.trim().length > 0 && this.registerEmail.includes('@') &&
      this.registerPassword.length >= 6;
  }

  private async submitAuth(): Promise<void> {
    if (!this.canSubmitAuth()) {
      return;
    }
    const context = this.appContext;
    if (!context) {
      return;
    }
    this.loading = true;
    try {
      const backendReady = await this.resolveBackend(false);
      if (!backendReady) {
        throw new Error('无法连接后端，请确认后端已启动并监听 0.0.0.0:8000。');
      }
      const session = this.authMode === 0
        ? await ApiClient.login(this.baseUrl, this.loginEmail.trim(), this.loginPassword)
        : await ApiClient.register(this.baseUrl, this.registerName.trim(), this.registerEmail.trim(), this.registerPassword);
      this.token = session.token;
      this.user = session.user;
      await StorageService.saveToken(context, session.token);
      await StorageService.saveUser(context, session.user);
      this.showToast('登录成功');
    } catch (err) {
      this.showToast(`登录失败：${(err as Error).message}`);
    }
    this.loading = false;
  }

  private async validateToken(showToast: boolean): Promise<void> {
    if (this.token.length === 0) {
      if (showToast) {
        this.showToast('未找到 Token');
      }
      return;
    }
    const context = this.appContext;
    if (!context) {
      return;
    }
    this.loading = true;
    const backendReady = await this.resolveBackend(showToast);
    if (!backendReady) {
      if (showToast) {
        this.showToast('无法连接后端，请确认后端已启动。');
      }
      this.loading = false;
      return;
    }
    try {
      this.baseUrl = normalizeBaseUrl(this.baseUrl);
      await StorageService.saveBaseUrl(context, this.baseUrl);
      const freshUser = await ApiClient.me(this.baseUrl, this.token);
      this.user = freshUser;
      await StorageService.saveUser(context, freshUser);
      if (showToast) {
        this.showToast('登录有效');
      }
    } catch (err) {
      const message = (err as Error).message;
      if (this.isAuthExpiredError(message)) {
        this.user = undefined;
        this.token = '';
        await StorageService.clearSession(context);
      }
      if (showToast) {
        this.showToast(this.isAuthExpiredError(message) ? '登录已失效' : `校验失败：${message}`);
      }
    }
    this.loading = false;
  }

  private openAgent(prompt: string): void {
    this.draft = prompt;
    this.currentTab = 1;
  }

  private newChat(): void {
    this.sessionId = makeId('session');
    this.messages = [
      {
        id: makeId('msg'),
        role: 'assistant',
        text: '新会话已开始。请输入你的简历、项目、岗位、面试回答或 Offer 信息。',
        createdAt: nowText()
      }
    ];
  }

  private async sendMessage(): Promise<void> {
    const text = this.draft.trim();
    if (text.length === 0 || this.loading) {
      return;
    }
    const context = this.appContext;
    if (!context) {
      return;
    }
    this.loading = true;
    this.draft = '';
    this.messages = this.messages.concat([{
      id: makeId('msg'),
      role: 'user',
      text: text,
      createdAt: nowText()
    }]);
    try {
      const backendReady = await this.resolveBackend(false);
      if (!backendReady) {
        throw new Error('无法连接后端，请确认后端已启动并监听 0.0.0.0:8000。');
      }
      const payload = await ApiClient.chat(this.baseUrl, this.token, text, this.sessionId);
      this.messages = this.messages.concat([{
        id: makeId('msg'),
        role: 'assistant',
        text: payload.displayText,
        createdAt: nowText()
      }]);
      if (this.autoSaveHistory) {
        await this.addHistory(payload, text);
      }
    } catch (err) {
      this.messages = this.messages.concat([{
        id: makeId('msg'),
        role: 'assistant',
        text: `请求失败：${(err as Error).message}`,
        createdAt: nowText()
      }]);
    }
    this.loading = false;
  }

  private async addHistory(payload: AssistantPayload, userMessage: string): Promise<void> {
    const context = this.appContext;
    if (!context) {
      return;
    }
    const title = this.makeHistoryTitle(payload.intent, userMessage);
    const record: HistoryRecord = {
      id: makeId('history'),
      title: title,
      intent: payload.intent,
      agent: payload.agent,
      userMessage: userMessage,
      assistantMessage: payload.message,
      resultText: payload.displayText,
      rawJson: payload.rawJson,
      createdAt: nowText()
    };
    this.history = [record].concat(this.history).slice(0, 80);
    await StorageService.saveHistory(context, this.history);
  }

  private makeHistoryTitle(intent: string, message: string): string {
    const first = message.split('\n').filter((item: string) => item.trim().length > 0)[0] ?? '';
    if (first.length > 6) {
      return first.length > 28 ? `${first.substring(0, 28)}...` : first;
    }
    return `${intentLabel(intent)}报告`;
  }

  private async saveAutoSave(): Promise<void> {
    const context = this.appContext;
    if (!context) {
      return;
    }
    await StorageService.saveAutoSave(context, this.autoSaveHistory);
  }

  private async logout(): Promise<void> {
    const context = this.appContext;
    if (context) {
      await StorageService.clearSession(context);
    }
    this.user = undefined;
    this.token = '';
    this.currentTab = 0;
    this.showToast('已退出登录');
  }

  private showToast(message: string): void {
    try {
      this.getUIContext().getPromptAction().showToast({ message: message });
    } catch (_err) {
    }
  }

  private async resolveBackend(showToast: boolean): Promise<boolean> {
    const context = this.appContext;
    const candidates = getBackendCandidateUrls(this.baseUrl);
    const reachableUrl = await ApiClient.findReachableBaseUrl(candidates);
    if (reachableUrl.length === 0) {
      return false;
    }
    this.baseUrl = normalizeBaseUrl(reachableUrl);
    if (context) {
      await StorageService.saveBaseUrl(context, this.baseUrl);
    }
    if (showToast) {
      this.showToast('后端连接正常');
    }
    return true;
  }

  private isAuthExpiredError(message: string): boolean {
    return message.includes('请先登录') || message.includes('重新登录') ||
      message.includes('登录已过期') || message.includes('账号不可用') ||
      message.includes('HTTP 401') || message.includes('HTTP 403');
  }
}
