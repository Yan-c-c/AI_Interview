"use client";

import Link from "next/link";
import { ChevronLeft, ChevronRight, Database, KeyRound, LogIn, Mail, Radar, ShieldCheck } from "lucide-react";
import type { FormEvent } from "react";
import { useRef, useState } from "react";
import BorderGlow from "@/components/BorderGlow";
import DotField from "@/components/DotField";
import MetallicPaint from "@/components/MetallicPaint";
import SplitText from "@/components/SplitText";

const LOGO_SRC = "/ai-interview-metal-logo.svg";
const LOGIN_STEPS = [
  { step: 1, label: "账号" },
  { step: 2, label: "密码" },
  { step: 3, label: "入口" },
] as const;

type LoginExperienceProps = {
  message?: string;
};

export default function LoginExperience({ message = "" }: LoginExperienceProps) {
  return (
    <main className="auth-page auth-page-dot auth-page-metal">
      <div className="auth-background" aria-hidden="true">
        <DotField
          dotRadius={1.5}
          dotSpacing={14}
          bulgeStrength={67}
          glowRadius={160}
          sparkle={false}
          waveAmplitude={0}
          cursorRadius={500}
          cursorForce={0.1}
          bulgeOnly
          gradientFrom="#a855f7"
          gradientTo="#b497cf"
          glowColor="#120f17"
        />
      </div>

      <section className="auth-stage auth-stage-metal">
        <div className="auth-hero-copy auth-hero-metal">
          <div className="auth-hero-logo" aria-hidden="true">
            <MetallicPaint
              imageSrc={LOGO_SRC}
              seed={42}
              scale={4}
              patternSharpness={1}
              noiseScale={0.5}
              speed={0.3}
              liquid={0.75}
              mouseAnimation={false}
              brightness={2}
              contrast={0.5}
              refraction={0.01}
              blur={0.015}
              chromaticSpread={2}
              fresnel={1}
              angle={0}
              waveAmplitude={1}
              distortion={1}
              contour={0.2}
              lightColor="#ffffff"
              darkColor="#000000"
              tintColor="#feb3ff"
            />
          </div>

          <SplitText
            text="智能面试助手"
            tag="h1"
            className="auth-hero-title"
            delay={48}
            duration={1.15}
            ease="power3.out"
            splitType="chars"
            from={{ opacity: 0, y: 38 }}
            to={{ opacity: 1, y: 0 }}
            threshold={0.1}
            rootMargin="-100px"
            textAlign="left"
          />

          <div className="auth-signal-grid" aria-label="系统能力">
            <span><ShieldCheck size={16} />角色鉴权</span>
            <span><Database size={16} />题库治理</span>
            <span><Radar size={16} />Agent 监控</span>
          </div>
        </div>

        <BorderGlow
          className="auth-glow-wrap"
          edgeSensitivity={30}
          glowColor="40 80 80"
          backgroundColor="#120F17"
          borderRadius={8}
          glowRadius={40}
          glowIntensity={1}
          coneSpread={25}
          animated
          colors={["#c084fc", "#f472b6", "#38bdf8"]}
        >
          <section className="auth-card auth-card-login auth-card-metal" aria-label="登录">
            <div className="auth-brand auth-brand-metal auth-brand-separated">
              <div className="auth-brand-logo" aria-hidden="true">
                <MetallicPaint
                  imageSrc={LOGO_SRC}
                  seed={42}
                  scale={4}
                  patternSharpness={1}
                  noiseScale={0.5}
                  speed={0.3}
                  liquid={0.75}
                  mouseAnimation={false}
                  brightness={2}
                  contrast={0.5}
                  refraction={0.01}
                  blur={0.015}
                  chromaticSpread={2}
                  fresnel={1}
                  angle={0}
                  waveAmplitude={1}
                  distortion={1}
                  contour={0.2}
                  lightColor="#ffffff"
                  darkColor="#000000"
                  tintColor="#feb3ff"
                />
              </div>
              <LoginCardIntro />
            </div>

            <LoginStepperForm message={message} />

            <div className="auth-foot">
              <span>还没有账号？</span>
              <Link href="/register">注册普通用户</Link>
            </div>
          </section>
        </BorderGlow>
      </section>
    </main>
  );
}

function LoginCardIntro() {
  return (
    <div className="auth-brand-text-detached">
      <h2 className="auth-card-title">登录账户</h2>
    </div>
  );
}

function LoginStepperForm({ message }: { message: string }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [direction, setDirection] = useState<"forward" | "back">("forward");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const emailInputRef = useRef<HTMLInputElement>(null);
  const passwordInputRef = useRef<HTMLInputElement>(null);
  const isLastStep = currentStep === LOGIN_STEPS.length;

  const validateCurrentStep = () => {
    if (currentStep === 1) {
      return emailInputRef.current?.reportValidity() ?? true;
    }

    if (currentStep === 2) {
      return passwordInputRef.current?.reportValidity() ?? true;
    }

    return true;
  };

  const goBack = () => {
    if (currentStep <= 1) return;
    setDirection("back");
    setCurrentStep(currentStep - 1);
  };

  const goNext = () => {
    if (!validateCurrentStep()) return;
    setDirection("forward");
    setCurrentStep(Math.min(currentStep + 1, LOGIN_STEPS.length));
  };

  const goToStep = (step: number) => {
    if (step >= currentStep) return;
    setDirection("back");
    setCurrentStep(step);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    if (!isLastStep) {
      event.preventDefault();
      goNext();
    }
  };

  return (
    <form className="auth-form auth-stepper-form" action="/api/auth/login" method="post" autoComplete="off" onSubmit={handleSubmit}>
      <input type="hidden" name="email" value={email} readOnly />
      <input type="hidden" name="password" value={password} readOnly />

      <div className="auth-stepper-card">
        <div className="auth-stepper-indicator-row" aria-label="登录步骤">
          {LOGIN_STEPS.map((item, index) => {
            const status = currentStep === item.step ? "active" : currentStep > item.step ? "complete" : "inactive";

            return (
              <div className="auth-stepper-indicator-group" key={item.step}>
                <button
                  type="button"
                  className={`auth-stepper-indicator ${status}`}
                  onClick={() => goToStep(item.step)}
                  disabled={item.step > currentStep}
                  aria-current={status === "active" ? "step" : undefined}
                  aria-label={`${item.label}${status === "complete" ? "已完成" : status === "active" ? "进行中" : "未开始"}`}
                >
                  <span className="auth-stepper-indicator-inner">
                    {status === "complete" ? <StepperCheckIcon /> : status === "active" ? <span className="auth-stepper-active-dot" /> : item.step}
                  </span>
                </button>
                {index < LOGIN_STEPS.length - 1 && (
                  <span className="auth-stepper-connector" aria-hidden="true">
                    <span className={currentStep > item.step ? "complete" : ""} />
                  </span>
                )}
              </div>
            );
          })}
        </div>

        <div className="auth-stepper-content" data-direction={direction}>
          {currentStep === 1 && (
            <div className="auth-step-panel" key="email">
              <div className="auth-step-copy">
                <span className="auth-step-kicker"><Mail size={14} />账号识别</span>
                <h3>输入登录邮箱</h3>
              </div>
              <label className="auth-step-field" htmlFor="login-email">
                邮箱
                <input
                  id="login-email"
                  ref={emailInputRef}
                  value={email}
                  onChange={event => setEmail(event.target.value)}
                  type="email"
                  autoComplete="off"
                  placeholder="请输入邮箱"
                  required
                />
              </label>
            </div>
          )}

          {currentStep === 2 && (
            <div className="auth-step-panel" key="password">
              <div className="auth-step-copy">
                <span className="auth-step-kicker"><KeyRound size={14} />身份校验</span>
                <h3>确认访问凭据</h3>
              </div>
              <label className="auth-step-field" htmlFor="login-password">
                密码
                <input
                  id="login-password"
                  ref={passwordInputRef}
                  value={password}
                  onChange={event => setPassword(event.target.value)}
                  type="password"
                  autoComplete="new-password"
                  placeholder="请输入密码"
                  required
                />
              </label>
            </div>
          )}

          {currentStep === 3 && (
            <div className="auth-step-panel" key="route">
              <div className="auth-step-copy">
                <span className="auth-step-kicker"><ShieldCheck size={14} />入口确认</span>
                <h3>准备进入系统</h3>
                <p>管理员进入后台，普通用户进入工作台。</p>
              </div>
              <div className="auth-step-summary" aria-label="登录摘要">
                <span><Mail size={16} />{email || "未填写邮箱"}</span>
                <span><ShieldCheck size={16} />按账号角色自动进入对应入口</span>
              </div>
            </div>
          )}
        </div>

        {message && <div className="auth-message auth-step-message">{message}</div>}

        <div className={`auth-stepper-footer ${currentStep === 1 ? "end" : "spread"}`}>
          {currentStep > 1 && (
            <button type="button" className="auth-stepper-back" onClick={goBack}>
              <ChevronLeft size={18} />
              上一步
            </button>
          )}
          {isLastStep ? (
            <button type="submit" className="auth-stepper-next auth-stepper-submit">
              <LogIn size={18} />
              登录
            </button>
          ) : (
            <button type="button" className="auth-stepper-next" onClick={goNext}>
              继续
              <ChevronRight size={18} />
            </button>
          )}
        </div>
      </div>
    </form>
  );
}

function StepperCheckIcon() {
  return (
    <svg className="auth-stepper-check" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}
