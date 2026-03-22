// TypeScript test file

interface ApiResponse<T> {
  data: T;
  error?: string;
}

async function fetchUser(id: number): Promise<ApiResponse<any>> {
  try {
    const res = await fetch(`/api/users/${id}`);
    return { data: await res.json() };
  } catch (err: unknown) {
    // Dark path: error swallowed, returns empty data
    return { data: null };
  }
}

class DatabaseClient {
  async query<T>(sql: string): Promise<T[]> {
    try {
      return await this.execute<T>(sql);
    } catch (e) {
      // Dark path: empty catch
    }
    return [];
  }

  private async execute<T>(sql: string): Promise<T[]> {
    return [];
  }

  async safeQuery(sql: string): Promise<any> {
    try {
      return await this.execute(sql);
    // @dark-path-ignore
    } catch (e) {
      return null;
    }
  }
}
