import { NextRequest, NextResponse } from "next/server";
import { clearAuthCookies, requestLocalUrl } from "@/lib/serverAuth";

export function GET(request: NextRequest) {
  const response = NextResponse.redirect(requestLocalUrl(request, "/login"), { status: 303 });
  clearAuthCookies(response);
  return response;
}
