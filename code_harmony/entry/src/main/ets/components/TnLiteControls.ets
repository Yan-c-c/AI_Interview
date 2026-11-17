import { AgentShortcut } from '../models/Models';

export const COLOR_BG = '#F5F7FA';
export const COLOR_PANEL = '#FFFFFF';
export const COLOR_TEXT = '#303133';
export const COLOR_SUB = '#606266';
export const COLOR_LINE = '#EBEEF5';
export const COLOR_PRIMARY = '#2979FF';

@Component
export struct TnLiteTag {
  @Prop text: string = '';
  @Prop color: string = COLOR_PRIMARY;

  build() {
    Text(this.text)
      .fontSize(11)
      .fontWeight(FontWeight.Medium)
      .fontColor(this.color)
      .padding({ left: 8, right: 8, top: 4, bottom: 4 })
      .backgroundColor(`${this.color}12`)
      .borderRadius(999)
      .border({ width: 1, color: `${this.color}20` });
  }
}

@Component
export struct TnLiteButton {
  @Prop text: string = '';
  @Prop icon: string = '';
  @Prop loading: boolean = false;
  @Prop disabled: boolean = false;
  @Prop plain: boolean = false;
  @Prop startColor: string = COLOR_PRIMARY;
  @Prop endColor: string = COLOR_PRIMARY;
  onTap: () => void = () => {};

  build() {
    Row({ space: 8 }) {
      if (this.loading) {
        LoadingProgress()
          .width(18)
          .height(18)
          .color(this.plain ? this.startColor : '#FFFFFF');
      } else if (this.icon.length > 0) {
        Text(this.icon)
          .fontSize(15);
      }
      Text(this.text)
        .fontSize(15)
        .fontWeight(FontWeight.Bold)
        .fontColor(this.plain ? this.startColor : '#FFFFFF');
    }
    .height(46)
    .width('100%')
    .justifyContent(FlexAlign.Center)
    .backgroundColor(this.plain ? '#FFFFFF' : this.startColor)
    .borderRadius(12)
    .border({ width: this.plain ? 1 : 0, color: this.plain ? COLOR_LINE : this.startColor })
    .opacity(this.disabled ? 0.52 : 1)
    .shadow(this.plain ? { radius: 0, color: '#00000000', offsetY: 0 } : { radius: 8, color: `${this.startColor}20`, offsetY: 4 })
    .onClick(() => {
      if (!this.disabled && !this.loading) {
        this.onTap();
      }
    });
  }
}

@Component
export struct TnLiteInput {
  @Link value: string;
  @Prop placeholder: string = '';
  @Prop isPassword: boolean = false;

  build() {
    TextInput({ text: this.value, placeholder: this.placeholder })
      .type(this.isPassword ? InputType.Password : InputType.Normal)
      .height(48)
      .width('100%')
      .fontSize(15)
      .fontColor(COLOR_TEXT)
      .placeholderColor('#909399')
      .padding({ left: 16, right: 16 })
      .backgroundColor('#FFFFFF')
      .borderRadius(10)
      .border({ width: 1, color: COLOR_LINE })
      .onChange((value: string) => {
        this.value = value;
      });
  }
}

@Component
export struct TnLiteTextArea {
  @Link value: string;
  @Prop placeholder: string = '';
  @Prop minHeight: number = 128;

  build() {
    Column() {
      TextArea({ text: this.value, placeholder: this.placeholder })
        .height(this.minHeight)
        .width('100%')
        .fontSize(15)
        .lineHeight(22)
        .fontColor(COLOR_TEXT)
        .placeholderColor('#909399')
        .backgroundColor(Color.Transparent)
        .padding({ left: 0, right: 0, top: 0, bottom: 0 })
        .onChange((value: string) => {
          this.value = value;
        });
      Row() {
        Blank();
        Text(`${this.value.length} 字`)
          .fontSize(12)
          .fontColor(COLOR_SUB);
      }
      .width('100%');
    }
    .width('100%')
    .padding(14)
    .backgroundColor('#FFFFFF')
    .borderRadius(12)
    .border({ width: 1, color: COLOR_LINE });
  }
}

@Component
export struct TnLiteEmpty {
  @Prop title: string = '';
  @Prop description: string = '';
  @Prop icon: string = '空';

  build() {
    Column({ space: 10 }) {
      Text(this.icon)
        .fontSize(18)
        .fontWeight(FontWeight.Bold)
        .fontColor(COLOR_PRIMARY)
        .width(46)
        .height(46)
        .textAlign(TextAlign.Center)
        .backgroundColor('#ECF5FF')
        .borderRadius(12);
      Text(this.title)
        .fontSize(17)
        .fontWeight(FontWeight.Bold)
        .fontColor(COLOR_TEXT);
      Text(this.description)
        .fontSize(13)
        .fontColor(COLOR_SUB)
        .textAlign(TextAlign.Center)
        .lineHeight(20);
    }
    .width('100%')
    .padding(24)
    .backgroundColor(COLOR_PANEL)
    .borderRadius(12)
    .border({ width: 1, color: COLOR_LINE });
  }
}

@Component
export struct AgentGradientCard {
  @Prop item: AgentShortcut = new AgentShortcut('', '', '', '', [COLOR_PRIMARY, '#ECF5FF'], '');
  onTap: (prompt: string) => void = (_prompt: string) => {};

  build() {
    Stack({ alignContent: Alignment.BottomStart }) {
      Column({ space: 12 }) {
        Row() {
          Text(this.item.icon)
            .fontSize(17)
            .fontWeight(FontWeight.Bold)
            .fontColor(this.item.colors[0])
            .width(44)
            .height(44)
            .textAlign(TextAlign.Center)
            .backgroundColor(this.item.colors[1])
            .borderRadius(10);
          Blank();
          Text('开始')
            .fontSize(12)
            .fontWeight(FontWeight.Medium)
            .fontColor(this.item.colors[0])
            .padding({ left: 10, right: 10, top: 5, bottom: 5 })
            .backgroundColor(this.item.colors[1])
            .borderRadius(999);
        }
        .width('100%');

        Text(this.item.title)
          .fontSize(17)
          .fontWeight(FontWeight.Bold)
          .fontColor(COLOR_TEXT);
        Text(this.item.subtitle)
          .fontSize(12)
          .fontColor(COLOR_SUB)
          .lineHeight(18)
          .maxLines(2);
      }
      .width('100%')
      .padding(14);
    }
    .width('48%')
    .height(146)
    .backgroundColor(COLOR_PANEL)
    .borderRadius(14)
    .border({ width: 1, color: COLOR_LINE })
    .clip(true)
    .shadow({ radius: 8, color: '#0000000A', offsetY: 3 })
    .margin({ bottom: 12 })
    .onClick(() => this.onTap(this.item.prompt));
  }
}

@Component
export struct GlassBottomTab {
  @Link currentIndex: number;

  build() {
    Row() {
      this.TabItem(0, '首页', '首');
      this.TabItem(1, '助手', 'AI');
      this.TabItem(2, '历史', '记');
      this.TabItem(3, '我的', '我');
    }
    .width('100%')
    .height(68)
    .padding({ left: 10, right: 10 })
    .backgroundColor('#FFFFFF')
    .borderRadius({ topLeft: 18, topRight: 18 })
    .border({ width: { top: 1 }, color: COLOR_LINE })
    .shadow({ radius: 10, color: '#0000000D', offsetY: -4 });
  }

  @Builder
  private TabItem(index: number, title: string, icon: string) {
    Column({ space: 4 }) {
      Text(icon)
        .fontSize(index === 1 ? 12 : 13)
        .fontWeight(FontWeight.Bold)
        .fontColor(this.currentIndex === index ? '#FFFFFF' : '#606266')
        .width(28)
        .height(28)
        .textAlign(TextAlign.Center)
        .backgroundColor(this.currentIndex === index ? COLOR_PRIMARY : '#F4F4F5')
        .borderRadius(index === 1 ? 9 : 14)
        .border({ width: this.currentIndex === index ? 0 : 1, color: this.currentIndex === index ? COLOR_PRIMARY : COLOR_LINE });
      Text(title)
        .fontSize(11)
        .fontWeight(this.currentIndex === index ? FontWeight.Bold : FontWeight.Regular)
        .fontColor(this.currentIndex === index ? COLOR_PRIMARY : '#909399');
    }
    .layoutWeight(1)
    .height(54)
    .justifyContent(FlexAlign.Center)
    .backgroundColor(Color.Transparent)
    .onClick(() => {
      this.currentIndex = index;
    });
  }
}
