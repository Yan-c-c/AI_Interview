import LoginExperience from "@/components/LoginExperience";

type PageProps = {
  searchParams?: Promise<{ error?: string | string[] }>;
};

export default async function LoginPage({ searchParams }: PageProps) {
  const params = searchParams ? await searchParams : {};
  const message = typeof params.error === "string" ? params.error : "";

  return <LoginExperience message={message} />;
}
