"use client";

import { ChangeEvent, useRef } from "react";
import { FileAudio, FileText, Upload } from "lucide-react";
import { UploadResult, uploadResumeFile } from "@/lib/api/assistant";

interface Props {
  file: UploadResult | null;
  loading: boolean;
  onLoadingChange: (loading: boolean) => void;
  onUploaded: (file: UploadResult) => void;
  onError: (message: string) => void;
}

export function FileUploader({ file, loading, onLoadingChange, onUploaded, onError }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0];
    if (!selected) return;
    onLoadingChange(true);
    try {
      const result = await uploadResumeFile(selected);
      onUploaded(result);
    } catch (error) {
      onError(error instanceof Error ? error.message : "文件上传失败");
    } finally {
      onLoadingChange(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="upload-box">
      <div className="upload-row">
        <div className="brand-row">
          {file?.is_audio ? <FileAudio size={20} /> : <FileText size={20} />}
          <div>
            <h3>{file?.filename || "上传简历 / 面试录音"}</h3>
            <p className="small muted">
              {file ? `${file.file_type.toUpperCase()} · ${file.is_audio ? "音频文件" : `${file.parsed_char_count} 字`}` : "支持 PDF、DOCX、TXT、MD、MP3、WAV、M4A"}
            </p>
          </div>
        </div>
        <input ref={inputRef} className="file-input" type="file" accept=".pdf,.docx,.txt,.md,.mp3,.wav,.m4a,.amr,.pcm,.flac,.aac,.ogg" onChange={handleChange} />
        <button className="ghost-button" type="button" disabled={loading} onClick={() => inputRef.current?.click()}>
          <Upload size={16} />
          {loading ? "解析中" : "选择文件"}
        </button>
      </div>
    </div>
  );
}
