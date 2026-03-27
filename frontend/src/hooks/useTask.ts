/* ─── ARC Platform — useTask Hook ─────────────────────────────────── */
"use client";
import { useCallback, useState } from "react";
import type { Task, TaskStep, TaskResult, TaskListResponse } from "@/types";
import { api } from "@/lib/api";

export function useTask() {
    const [tasks, setTasks] = useState<Task[]>([]);
    const [currentTask, setCurrentTask] = useState<Task | null>(null);
    const [steps, setSteps] = useState<TaskStep[]>([]);
    const [result, setResult] = useState<TaskResult | null>(null);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchTasks = useCallback(async (page = 1, status?: string) => {
        setLoading(true);
        setError(null);
        try {
            const data: TaskListResponse = await api.getTasks(page, 20, status);
            setTasks(data.tasks);
            setTotal(data.total);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchTask = useCallback(async (taskId: string) => {
        setLoading(true);
        try {
            const data = await api.getTask(taskId);
            setCurrentTask(data);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchSteps = useCallback(async (taskId: string) => {
        try {
            const data = await api.getTaskSteps(taskId);
            setSteps(data.steps || []);
        } catch (e: any) {
            setError(e.message);
        }
    }, []);

    const fetchResult = useCallback(async (taskId: string) => {
        try {
            const data = await api.getTaskResult(taskId);
            setResult(data);
        } catch (e: any) {
            setError(e.message);
        }
    }, []);

    const createTask = useCallback(async (title: string, description: string, budget?: number, tags?: string[]) => {
        setLoading(true);
        try {
            const data = await api.createTask(title, description, budget, tags);
            setCurrentTask(data);
            return data;
        } catch (e: any) {
            setError(e.message);
            throw e;
        } finally {
            setLoading(false);
        }
    }, []);

    return {
        tasks, total, currentTask, steps, result,
        loading, error,
        fetchTasks, fetchTask, fetchSteps, fetchResult, createTask,
    };
}
