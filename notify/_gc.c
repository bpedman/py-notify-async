/*--------------------------------------------------------------------*\
 * This file is part of Py-notify.                                    *
 *                                                                    *
 * Copyright (C) 2007, 2008 Paul Pogonyshev.                          *
 *                                                                    *
 * This library is free software; you can redistribute it and/or      *
 * modify it under the terms of the GNU Lesser General Public License *
 * as published by the Free Software Foundation; either version 2.1   *
 * of the License, or (at your option) any later version.             *
 *                                                                    *
 * This library is distributed in the hope that it will be useful,    *
 * but WITHOUT ANY WARRANTY; without even the implied warranty of     *
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU  *
 * Lesser General Public License for more details.                    *
 *                                                                    *
 * You should have received a copy of the GNU Lesser General Public   *
 * License along with this library; if not, write to the Free         *
 * Software Foundation, Inc., 51 Franklin Street, Fifth Floor,        *
 * Boston, MA 02110-1301 USA                                          *
\*--------------------------------------------------------------------*/


#include <Python.h>


/* See Python documentation for why it prevents rare and very obscure bug.  Need to
 * backport for older Python versions.
 */
#ifdef Py_CLEAR
#  define Compatibility_CLEAR(object) Py_CLEAR (object)
#else
#  define Compatibility_CLEAR(object)                   \
     do                                                 \
       {                                                \
         if (object)                                    \
           {                                            \
             PyObject *temp = (PyObject *) (object);    \
             (object) = NULL;                           \
             Py_DECREF (temp);                          \
           }                                            \
       }                                                \
     while (0)
#endif

/* Py_VISIT is not available in 2.3. */
#ifdef Py_VISIT
#  define Compatibility_VISIT(object) Py_VISIT (object)
#else
#  define Compatibility_VISIT(object)                           \
     do                                                         \
       {                                                        \
         if (object)                                            \
           {                                                    \
             int result = visit ((PyObject *) (object), arg);   \
             if (result)                                        \
               return result;                                   \
           }                                                    \
       }                                                        \
     while (0)
#endif


/* Needed for Py3k, not defined earlier. */
#ifdef PyVarObject_HEAD_INIT
#  define Compatibility_VarObject_HEAD_INIT(ob_size) PyVarObject_HEAD_INIT (0, ob_size)
#else
#  define Compatibility_VarObject_HEAD_INIT(ob_size) PyObject_HEAD_INIT (0) ob_size,
#endif


/* Another difference between 2.x and 3.x. */
#if defined (PY_MAJOR_VERSION) && PY_MAJOR_VERSION >= 3
#  define Compatibility_Type_Type(type) (type).ob_base.ob_base.ob_type
#else
#  define Compatibility_Type_Type(type) (type).ob_type
#endif


#ifdef Py_TPFLAGS_HAVE_VERSION_TAG
#  define Compatibility_TPFLAGS_HAVE_VERSION_TAG Py_TPFLAGS_HAVE_VERSION_TAG
#else
#  define Compatibility_TPFLAGS_HAVE_VERSION_TAG 0
#endif


/* Working around more changes in Py3k: module initialization. */
#ifdef PyMODINIT_FUNC
#  define Compatibility_MODINIT_FUNC PyMODINIT_FUNC
#else
#  ifdef DL_EXPORT
#    define Compatibility_MODINIT_FUNC DL_EXPORT (void)
#  else
#    define Compatibility_MODINIT_FUNC void
#  endif
#endif


#ifdef PyModuleDef_HEAD_INIT

#  define Compatibility_ModuleDef                 PyModuleDef
#  define Compatibility_ModuleDef_HEAD_INIT       PyModuleDef_HEAD_INIT
#  define Compatibility_MODINIT_FUNC_NAME(module) PyInit_##module

#  define Compatibility_ModuleCreate(definition)  PyModule_Create (definition)
#  define Compatibility_ModulePostCreate(module, definition)     \
     (PyModule_AddStringConstant ((module), "__docformat__",     \
                                  "epytext en") == 0)

#  define Compatibility_ModuleReturn(module)      return (module)

#  define Compatibility_ModuleState(def, module, type)           \
     ((type *) PyModule_GetState (module))
#  define Compatibility_ModuleStateFromDef(def, type)            \
     ((type *) PyModule_GetState (PyState_FindModule (&def)))

#else  /* !defined PyMODINIT_FUNC */

typedef
struct
{
  const int      dummy;
  const char    *m_name;
  const char    *m_doc;
  int            m_size;
  PyMethodDef   *m_methods;
  inquiry        m_reload;
  traverseproc   m_traverse;
  inquiry        m_clear;
  freefunc       m_free;
}
Compatibility_ModuleDef;

#  define Compatibility_ModuleDef_HEAD_INIT       0
#  define Compatibility_MODINIT_FUNC_NAME(module) init##module

#  define Compatibility_ModuleCreate(definition)                        \
     Py_InitModule ((char *) (definition)->m_name, NULL)
#  define Compatibility_ModulePostCreate(module, definition)            \
     (PyModule_AddStringConstant ((module), "__doc__",                  \
                                  (char *) (definition)->m_doc) == 0    \
      && PyModule_AddStringConstant ((module), "__docformat__",         \
                                     "epytext en") == 0)

#  define Compatibility_ModuleReturn(module)      return

#  define Compatibility_ModuleState(def, module, type)                  \
     (&__2_x_state__##def)
#  define Compatibility_ModuleStateFromDef(def, type)                   \
     (&__2_x_state__##def)
#  define Compatibility_2_x_MODULE_STATE          1


#endif  /* !defined PyMODINIT_FUNC */


/* Also compatibility, but let's avoid long name in this case. */
#if defined (PY_MAJOR_VERSION) && PY_MAJOR_VERSION >= 3
#  define PyInt_AsLong   PyLong_AsLong
#  define PyInt_FromLong PyLong_FromLong
#endif



/*- Type forward declarations --------------------------------------*/

typedef
struct
{
  PyObject_HEAD
  PyObject *  __dict__;
  PyObject *  __weakref__;
}
AbstractGCProtector;


typedef
struct
{
  AbstractGCProtector  base;
  long int             num_active_protections;
}
FastGCProtector;


typedef
struct
{
  AbstractGCProtector  base;
  /* Note: no cyclic GC support is needed, because this dict is for internal use only. */
  PyObject *           protected_objects_dict;
  long int             num_active_protections;
}
RaisingGCProtector;


typedef  RaisingGCProtector  DebugGCProtector;


typedef
struct
{
  PyObject *           unprotection_error_type;
  PyTypeObject *       abstract_gc_protector_type;
}
GCModuleState;



/*- Functions forward declarations ---------------------------------*/

static int          FastGCProtector_init            (FastGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static void         FastGCProtector_dealloc         (FastGCProtector *self);
static PyObject *   FastGCProtector_protect         (FastGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   FastGCProtector_unprotect       (FastGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   FastGCProtector_get_num_active_protections
                      (FastGCProtector *self);

static int          RaisingGCProtector_init         (RaisingGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static void         RaisingGCProtector_dealloc      (RaisingGCProtector *self);
static PyObject *   RaisingGCProtector_protect      (RaisingGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   RaisingGCProtector_unprotect    (RaisingGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   RaisingGCProtector_get_num_object_protections
                                                    (RaisingGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   RaisingGCProtector_get_num_protected_objects
                      (RaisingGCProtector *self);
static PyObject *   RaisingGCProtector_get_num_active_protections
                      (RaisingGCProtector *self);

static PyObject *   DebugGCProtector_unprotect      (DebugGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);

static int          gc_module_initialize_state      (PyObject *self);
static int          gc_module_traverse              (PyObject *self, visitproc visit, void *arg);
static int          gc_module_clear                 (PyObject *self);



/*- Documentation --------------------------------------------------*/

#define MODULE_DOC "Internal helper module for C{L{notify.gc}}.  Do not use directly."


#define FAST_GC_PROTECTOR_DOC "\
Default fast implementation of C{AbstractGCProtector} interface.  It is suitable for \
production use, but difficult to debug problems with, because it doesn't track what has and \
what has not be protected.  For that purpose, use C{L{RaisingGCProtector}} or \
C{L{DebugGCProtector}}."

#define FAST_GC_PROTECTOR_PROTECT_DOC                                   \
  NULL

#define FAST_GC_PROTECTOR_UNPROTECT_DOC                                 \
  NULL

#define FAST_GC_PROTECTOR_NUM_ACTIVE_PROTECTIONS_DOC "\
Number of protections currently in effect.  This number can be larger than the number of distinct \
protected objects.  Actually, since C{FastGCProtector} doesn't track protected objects, it cannot \
determine number of protected objects in principle.  Use C{L{RaisingGCProtector}} or a subclass \
if you need that information."


#define RAISING_GC_PROTECTOR_DOC "\
Implementation of C{AbstractGCProtector} interface suitable for aggressively debugging \
possible problems.  Instances of this class track what they have protected so far and how \
many times.  If you try to unprotect an object more times than it has been protected, an \
exception will be raised.\n\
\n\
There is also a number of functions and properties in this class that allow you to retrieve \
various protection information.\n\
\n\
@see: C{L{DebugGCProtector}}"

#define RAISING_GC_PROTECTOR_PROTECT_DOC                                \
  NULL

#define RAISING_GC_PROTECTOR_UNPROTECT_DOC                              \
  NULL

#define RAISING_GC_PROTECTOR_GET_NUM_OBJECT_PROTECTIONS "\
get_num_object_protections(self, object) \
\n\
Get the number of times given C{object} is protected, i.e. number of times it has to be \
L{unprotected <unprotect>} to become a legal target for garbage collection again."

#define RAISING_GC_PROTECTOR_NUM_PROTECTED_OBJECTS_DOC "\
Number of distinct objects currently protected.  I.e. number of times each particular object is \
protected is not relevant for this property.\n\
\n\
@see: C{L{num_active_protections}}"

#define RAISING_GC_PROTECTOR_NUM_ACTIVE_PROTECTIONS_DOC                 \
  NULL


#define DEBUG_GC_PROTECTOR_DOC "\
Implementation of C{AbstractGCProtector} interface suitable for debugging possible problems. \
Instances of this class track what they have protected so far and how many times.  If you try to \
unprotect an object more times than it has been protected, a stack trace will be printed and \
nothing will be done.  Note that unlike C{L{RaisingGCProtector}}, no exception will be thrown.\n\
\n\
There is also a number of functions and properties in this class that allow you to retrieve \
various protection information.\n\
\n\
@see: C{L{RaisingGCProtector}}"

#define DEBUG_GC_PROTECTOR_UNPROTECT_DOC                                \
  NULL



/*- Types ----------------------------------------------------------*/

static PyMethodDef  FastGCProtector_methods[]
  = { { "protect",     (PyCFunction) FastGCProtector_protect,
        METH_VARARGS | METH_KEYWORDS, FAST_GC_PROTECTOR_PROTECT_DOC },
      { "unprotect",   (PyCFunction) FastGCProtector_unprotect,
        METH_VARARGS | METH_KEYWORDS, FAST_GC_PROTECTOR_UNPROTECT_DOC },
      { NULL, NULL, 0, NULL } };

static PyGetSetDef  FastGCProtector_properties[]
  = { { "num_active_protections", (getter) FastGCProtector_get_num_active_protections, NULL,
        FAST_GC_PROTECTOR_NUM_ACTIVE_PROTECTIONS_DOC, NULL },
      { NULL, NULL, NULL, NULL, NULL } };

static PyTypeObject  FastGCProtector_Type
  = { Compatibility_VarObject_HEAD_INIT (0)
      "notify._gc.FastGCProtector",                  /* tp_name           */
      sizeof (FastGCProtector),                      /* tp_basicsize      */
      0,                                             /* tp_itemsize       */
      (destructor)     FastGCProtector_dealloc,      /* tp_dealloc        */
      (printfunc)      0,                            /* tp_print          */
      (getattrfunc)    0,                            /* tp_getattr        */
      (setattrfunc)    0,                            /* tp_setattr        */
      (cmpfunc)        0,                            /* tp_compare        */
      (reprfunc)       0,                            /* tp_repr           */
      0,                                             /* tp_as_number      */
      0,                                             /* tp_as_sequence    */
      0,                                             /* tp_as_mapping     */
      (hashfunc)       0,                            /* tp_hash           */
      (ternaryfunc)    0,                            /* tp_call           */
      (reprfunc)       0,                            /* tp_str            */
      (getattrofunc)   0,                            /* tp_getattro       */
      (setattrofunc)   0,                            /* tp_setattro       */
      0,                                             /* tp_as_buffer      */
      Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Compatibility_TPFLAGS_HAVE_VERSION_TAG,
                                                     /* tp_flags          */
      FAST_GC_PROTECTOR_DOC,                         /* tp_doc            */
      (traverseproc)   0,                            /* tp_traverse       */
      (inquiry)        0,                            /* tp_clear          */
      (richcmpfunc)    0,                            /* tp_richcompare    */
      0,                                             /* tp_weaklistoffset */
      (getiterfunc)    0,                            /* tp_iter           */
      (iternextfunc)   0,                            /* tp_iternext       */
      FastGCProtector_methods,                       /* tp_methods        */
      0,                                             /* tp_members        */
      FastGCProtector_properties,                    /* tp_getset         */
      0  /* Actual value is set in runtime. */,      /* tp_base           */
      (PyObject *)     0,                            /* tp_dict           */
      0,                                             /* tp_descr_get      */
      0,                                             /* tp_descr_set      */
      0,                                             /* tp_dictoffset     */
      (initproc)       FastGCProtector_init,         /* tp_init           */
      (allocfunc)      0,                            /* tp_alloc          */
      (newfunc)        0,                            /* tp_new            */
      (freefunc)       0,                            /* tp_free           */
      (inquiry)        0,                            /* tp_is_gc          */
      (PyObject *)     0,                            /* tp_bases          */
    };


static PyMethodDef  RaisingGCProtector_methods[]
  = { { "protect",     (PyCFunction) RaisingGCProtector_protect,
        METH_VARARGS | METH_KEYWORDS, RAISING_GC_PROTECTOR_PROTECT_DOC },
      { "unprotect",   (PyCFunction) RaisingGCProtector_unprotect,
        METH_VARARGS | METH_KEYWORDS, RAISING_GC_PROTECTOR_UNPROTECT_DOC },
      { "get_num_object_protections", (PyCFunction) RaisingGCProtector_get_num_object_protections,
        METH_VARARGS | METH_KEYWORDS, RAISING_GC_PROTECTOR_GET_NUM_OBJECT_PROTECTIONS },
      { NULL, NULL, 0, NULL } };

static PyGetSetDef  RaisingGCProtector_properties[]
  = { { "num_protected_objects", (getter) RaisingGCProtector_get_num_protected_objects, NULL,
        RAISING_GC_PROTECTOR_NUM_PROTECTED_OBJECTS_DOC, NULL },
      { "num_active_protections", (getter) RaisingGCProtector_get_num_active_protections, NULL,
        RAISING_GC_PROTECTOR_NUM_ACTIVE_PROTECTIONS_DOC, NULL },
      { NULL, NULL, NULL, NULL, NULL } };

static PyTypeObject  RaisingGCProtector_Type
  = { Compatibility_VarObject_HEAD_INIT (0)
      "notify._gc.RaisingGCProtector",               /* tp_name           */
      sizeof (RaisingGCProtector),                   /* tp_basicsize      */
      0,                                             /* tp_itemsize       */
      (destructor)     RaisingGCProtector_dealloc,   /* tp_dealloc        */
      (printfunc)      0,                            /* tp_print          */
      (getattrfunc)    0,                            /* tp_getattr        */
      (setattrfunc)    0,                            /* tp_setattr        */
      (cmpfunc)        0,                            /* tp_compare        */
      (reprfunc)       0,                            /* tp_repr           */
      0,                                             /* tp_as_number      */
      0,                                             /* tp_as_sequence    */
      0,                                             /* tp_as_mapping     */
      (hashfunc)       0,                            /* tp_hash           */
      (ternaryfunc)    0,                            /* tp_call           */
      (reprfunc)       0,                            /* tp_str            */
      (getattrofunc)   0,                            /* tp_getattro       */
      (setattrofunc)   0,                            /* tp_setattro       */
      0,                                             /* tp_as_buffer      */
      Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Compatibility_TPFLAGS_HAVE_VERSION_TAG,
                                                     /* tp_flags          */
      RAISING_GC_PROTECTOR_DOC,                      /* tp_doc            */
      (traverseproc)   0,                            /* tp_traverse       */
      (inquiry)        0,                            /* tp_clear          */
      (richcmpfunc)    0,                            /* tp_richcompare    */
      0,                                             /* tp_weaklistoffset */
      (getiterfunc)    0,                            /* tp_iter           */
      (iternextfunc)   0,                            /* tp_iternext       */
      RaisingGCProtector_methods,                    /* tp_methods        */
      0,                                             /* tp_members        */
      RaisingGCProtector_properties,                 /* tp_getset         */
      0  /* Actual value is set in runtime. */,      /* tp_base           */
      (PyObject *)     0,                            /* tp_dict           */
      0,                                             /* tp_descr_get      */
      0,                                             /* tp_descr_set      */
      0,                                             /* tp_dictoffset     */
      (initproc)       RaisingGCProtector_init,      /* tp_init           */
      (allocfunc)      0,                            /* tp_alloc          */
      (newfunc)        0,                            /* tp_new            */
      (freefunc)       0,                            /* tp_free           */
      (inquiry)        0,                            /* tp_is_gc          */
      (PyObject *)     0,                            /* tp_bases          */
    };


static PyMethodDef  DebugGCProtector_methods[]
  = { { "unprotect",   (PyCFunction) DebugGCProtector_unprotect,
        METH_VARARGS | METH_KEYWORDS, DEBUG_GC_PROTECTOR_UNPROTECT_DOC },
      { NULL, NULL, 0, NULL } };

static PyTypeObject  DebugGCProtector_Type
  = { Compatibility_VarObject_HEAD_INIT (0)
      "notify._gc.DebugGCProtector",                 /* tp_name           */
      sizeof (DebugGCProtector),                     /* tp_basicsize      */
      0,                                             /* tp_itemsize       */
      (destructor)     0,                            /* tp_dealloc        */
      (printfunc)      0,                            /* tp_print          */
      (getattrfunc)    0,                            /* tp_getattr        */
      (setattrfunc)    0,                            /* tp_setattr        */
      (cmpfunc)        0,                            /* tp_compare        */
      (reprfunc)       0,                            /* tp_repr           */
      0,                                             /* tp_as_number      */
      0,                                             /* tp_as_sequence    */
      0,                                             /* tp_as_mapping     */
      (hashfunc)       0,                            /* tp_hash           */
      (ternaryfunc)    0,                            /* tp_call           */
      (reprfunc)       0,                            /* tp_str            */
      (getattrofunc)   0,                            /* tp_getattro       */
      (setattrofunc)   0,                            /* tp_setattro       */
      0,                                             /* tp_as_buffer      */
      Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Compatibility_TPFLAGS_HAVE_VERSION_TAG,
                                                     /* tp_flags          */
      DEBUG_GC_PROTECTOR_DOC,                        /* tp_doc            */
      (traverseproc)   0,                            /* tp_traverse       */
      (inquiry)        0,                            /* tp_clear          */
      (richcmpfunc)    0,                            /* tp_richcompare    */
      0,                                             /* tp_weaklistoffset */
      (getiterfunc)    0,                            /* tp_iter           */
      (iternextfunc)   0,                            /* tp_iternext       */
      DebugGCProtector_methods,                      /* tp_methods        */
      0,                                             /* tp_members        */
      0,                                             /* tp_getset         */
      (PyTypeObject *) &RaisingGCProtector_Type,     /* tp_base           */
      (PyObject *)     0,                            /* tp_dict           */
      0,                                             /* tp_descr_get      */
      0,                                             /* tp_descr_set      */
      0,                                             /* tp_dictoffset     */
      (initproc)       0,                            /* tp_init           */
      (allocfunc)      0,                            /* tp_alloc          */
      (newfunc)        0,                            /* tp_new            */
      (freefunc)       0,                            /* tp_free           */
      (inquiry)        0,                            /* tp_is_gc          */
      (PyObject *)     0,                            /* tp_bases          */
    };



/*- Static variables -----------------------------------------------*/

static Compatibility_ModuleDef  gc_module
  = { Compatibility_ModuleDef_HEAD_INIT,
      "notify._gc",
      MODULE_DOC,
      sizeof (GCModuleState),
      NULL,
      NULL,
      gc_module_traverse,
      gc_module_clear,
      NULL };

#define GC_MODULE_STATE(module)    Compatibility_ModuleState (gc_module, module, GCModuleState)
#define GC_MODULE_STATE_FROM_DEF() Compatibility_ModuleStateFromDef (gc_module, GCModuleState)

#if Compatibility_2_x_MODULE_STATE
static GCModuleState __2_x_state__gc_module
  = { NULL, NULL };
#endif


static char *  no_keywords[]     = { NULL };
static char *  object_keywords[] = { "object", NULL };



/*- FastGCProtector type methods -----------------------------------*/

static int
FastGCProtector_init (FastGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  if (!PyArg_ParseTupleAndKeywords (arguments, keywords, ":notify._gc.FastGCProtector",
                                    no_keywords))
    return -1;

  return 0;
}


static void
FastGCProtector_dealloc (FastGCProtector *self)
{
  ((PyObject *) self)->ob_type->tp_free ((PyObject *) self);
}


static PyObject *
FastGCProtector_protect (FastGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify._gc.FastGCProtector.protect",
                                    object_keywords, &object))
    return NULL;

  if (object != Py_None)
    {
      Py_INCREF (object);
      ++self->num_active_protections;
    }

  Py_INCREF (object);
  return object;
}


static PyObject *
FastGCProtector_unprotect (FastGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify._gc.FastGCProtector.protect",
                                    object_keywords, &object))
    return NULL;

  if (object != Py_None)
    --self->num_active_protections;
  else
    Py_INCREF (object);

  /* `object' reference counter is implicitly decremented by below return statement. */
  return object;
}


static PyObject *
FastGCProtector_get_num_active_protections (FastGCProtector *self)
{
  return PyInt_FromLong (self->num_active_protections);
}



/*- RaisingGCProtector type methods --------------------------------*/

static int
RaisingGCProtector_init (RaisingGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  if (!PyArg_ParseTupleAndKeywords (arguments, keywords, ":notify._gc.RaisingGCProtector",
                                    no_keywords))
    return -1;

  Compatibility_CLEAR (self->protected_objects_dict);
  self->protected_objects_dict = PyDict_New ();

  if (!self->protected_objects_dict)
    return -1;

  return 0;
}


static void
RaisingGCProtector_dealloc (RaisingGCProtector *self)
{
  Compatibility_CLEAR (self->protected_objects_dict);
  ((PyObject *) self)->ob_type->tp_free ((PyObject *) self);
}


static PyObject *
RaisingGCProtector_protect (RaisingGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify._gc.RaisingGCProtector.protect",
                                    object_keywords, &object))
    return NULL;

  if (object != Py_None)
    {
      PyObject *id;
      PyObject *num_protections;
      long int  num_protections_new;

      id = PyLong_FromVoidPtr (object);
      if (!id)
        return NULL;

      num_protections = PyDict_GetItem (self->protected_objects_dict, id);

      if (num_protections)
        num_protections_new = PyInt_AsLong (num_protections) + 1;
      else
        num_protections_new = 1;

      num_protections = PyInt_FromLong (num_protections_new);
      if (!num_protections)
        {
          Py_DECREF (id);
          return NULL;
        }

      PyDict_SetItem (self->protected_objects_dict, id, num_protections);
      Py_DECREF (num_protections);

      Py_DECREF (id);

      /* Do protect finally. */
      Py_INCREF (object);
      ++self->num_active_protections;
    }

  Py_INCREF (object);
  return object;
}


static PyObject *
RaisingGCProtector_unprotect (RaisingGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  GCModuleState *state = GC_MODULE_STATE_FROM_DEF ();
  PyObject      *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify._gc.RaisingGCProtector.unprotect",
                                    object_keywords, &object))
    return NULL;

  if (object != Py_None)
    {
      PyObject *id;
      PyObject *num_protections;

      id = PyLong_FromVoidPtr (object);
      if (!id)
        return NULL;

      num_protections = PyDict_GetItem (self->protected_objects_dict, id);

      if (num_protections)
        {
          long int  num_protections_new = PyInt_AsLong (num_protections) - 1;

          if (num_protections_new)
            {
              num_protections = PyInt_FromLong (num_protections_new);
              if (!num_protections)
                {
                  Py_DECREF (id);
                  return NULL;
                }

              PyDict_SetItem (self->protected_objects_dict, id, num_protections);
              Py_DECREF (num_protections);
            }
          else
            PyDict_DelItem (self->protected_objects_dict, id);

          Py_DECREF (id);
          --self->num_active_protections;
        }
      else
        {
          const char *type_name = ((PyObject *) self)->ob_type->tp_name;

          if (type_name)
            {
              type_name = strrchr (type_name, '.');

              if (type_name)
                type_name += 1;
              else
                type_name = ((PyObject *) self)->ob_type->tp_name;
            }
          else
            type_name = "?";

          PyErr_Format (state->unprotection_error_type,
                        "object is not protected by this %s", type_name);

          Py_DECREF (id);
          return NULL;
        }
    }
  else
    {
      /* So that the return statement at the end does no implicit unprotection. */
      Py_INCREF (object);
    }

  /* `object' reference counter is implicitly decremented by below return statement. */
  return object;
}


static PyObject *
RaisingGCProtector_get_num_object_protections (RaisingGCProtector *self,
                                               PyObject *arguments, PyObject *keywords)
{
  PyObject *object;
  PyObject *id;
  PyObject *num_protections;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify._gc.RaisingGCProtector.unprotect",
                                    object_keywords, &object))
    return NULL;

  id = PyLong_FromVoidPtr (object);
  if (!id)
    return NULL;

  num_protections = PyDict_GetItem (self->protected_objects_dict, id);

  if (num_protections)
    {
      Py_INCREF (num_protections);
      return num_protections;
    }
  else
    return PyInt_FromLong (0);
}


static PyObject *
RaisingGCProtector_get_num_protected_objects (RaisingGCProtector *self)
{
  return PyInt_FromLong (PyDict_Size (self->protected_objects_dict));
}


static PyObject *
RaisingGCProtector_get_num_active_protections (RaisingGCProtector *self)
{
  return PyInt_FromLong (self->num_active_protections);
}



/*- DebugGCProtector type methods ----------------------------------*/

static PyObject *
DebugGCProtector_unprotect (DebugGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  /* For a proper exception message and so we can assume that if super unprotect() method
   * fails, than it is because object is not protected, not because of wrong arguments.
   */
  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify._gc.DebugGCProtector.unprotect",
                                    object_keywords, &object))
    return NULL;

  if (!RaisingGCProtector_unprotect (self, arguments, keywords))
    {
      PyErr_Print ();
      PyErr_Clear ();

      /* So that the return statement does no implicit unprotection. */
      Py_INCREF (object);
    }

  return object;
}



/*- Module functions -----------------------------------------------*/

static int
gc_module_initialize_state (PyObject *self)
{
  GCModuleState *state            = GC_MODULE_STATE (self);
  PyObject      *main_module      = NULL;
  PyObject      *main_module_dict = NULL;

  main_module = PyImport_ImportModule ("notify.gc");
  if (!main_module)
    goto error;

  main_module_dict = PyModule_GetDict (main_module);
  if (!main_module_dict)
    goto error;

  state->unprotection_error_type = PyDict_GetItemString (main_module_dict, "UnprotectionError");
  if (!state->unprotection_error_type)
    goto error;

  Py_INCREF (state->unprotection_error_type);

  state->abstract_gc_protector_type
    = (PyTypeObject *) PyDict_GetItemString (main_module_dict, "AbstractGCProtector");
  if (!state->abstract_gc_protector_type)
    goto error;

  if (state->abstract_gc_protector_type   ->tp_basicsize != sizeof (AbstractGCProtector)
      || state->abstract_gc_protector_type->tp_itemsize  != 0)
    {
      printf ("%d %d\n", state->abstract_gc_protector_type->tp_basicsize, sizeof (AbstractGCProtector));
      PyErr_SetString (PyExc_RuntimeError,
                       "AbstractGCProtector must not have any slots (except for __dict__ and "
                       "__weakref__) for proper subclassing in the extension");
      goto error;
    }

  Py_INCREF (state->abstract_gc_protector_type);

  Py_DECREF (main_module);
  Py_DECREF (main_module_dict);

  return 0;

 error:
  Py_XDECREF (main_module);
  Py_XDECREF (main_module_dict);
  gc_module_clear (self);

  return -1;
}

static int
gc_module_traverse (PyObject *self, visitproc visit, void *arg)
{
  GCModuleState *state = GC_MODULE_STATE (self);

  Compatibility_VISIT (state->unprotection_error_type);
  Compatibility_VISIT (state->abstract_gc_protector_type);

  return 0;
}

static int
gc_module_clear (PyObject *self)
{
  GCModuleState *state = GC_MODULE_STATE (self);

  Compatibility_CLEAR (state->unprotection_error_type);
  Compatibility_CLEAR (state->abstract_gc_protector_type);

  return 0;
}



/*- Module initialization ------------------------------------------*/

#define REGISTER_TYPE(dictionary, type, meta_type, name, error_label)   \
  do                                                                    \
    {                                                                   \
      Compatibility_Type_Type (type) = meta_type;                       \
      type.tp_alloc = PyType_GenericAlloc;                              \
      type.tp_new   = PyType_GenericNew;                                \
      if (PyType_Ready (&type) == -1                                    \
          || (PyDict_SetItemString (dictionary, name,                   \
                                    (PyObject *) &type)                 \
              == -1))                                                   \
        goto error_label;                                               \
    }                                                                   \
  while (0)


Compatibility_MODINIT_FUNC
Compatibility_MODINIT_FUNC_NAME (_gc) (void)
{
  PyObject      *module = NULL;
  PyObject      *dictionary;
  GCModuleState *state;
  PyTypeObject  *meta_type;

  module = Compatibility_ModuleCreate (&gc_module);
  if (!module)
    goto error;

  state = GC_MODULE_STATE (module);

  /* PEP 3121 claims that the state will be zero-initialized, but at least currently this
   * doesn't happen.  Maybe a bug in Py3k.
   */
  memset (state, 0, sizeof (GCModuleState));

  if (!Compatibility_ModulePostCreate (module, &gc_module))
    goto error;

  if (gc_module_initialize_state (module) == -1)
    goto error;

  /* FIXME: This practically ruins module state separation.  However, PEP 3121 is not
   *        fully implemented in 3.0 anyway, so let's not care for now.
   */
  meta_type                       = Compatibility_Type_Type (*state->abstract_gc_protector_type);
  FastGCProtector_Type   .tp_base = state->abstract_gc_protector_type;
  RaisingGCProtector_Type.tp_base = state->abstract_gc_protector_type;

  dictionary = PyModule_GetDict (module);
  if (!dictionary)
    goto error;

  REGISTER_TYPE (dictionary, FastGCProtector_Type,     meta_type, "FastGCProtector",     error);
  REGISTER_TYPE (dictionary, RaisingGCProtector_Type,  meta_type, "RaisingGCProtector",  error);
  REGISTER_TYPE (dictionary, DebugGCProtector_Type,    meta_type, "DebugGCProtector",    error);

  goto do_return;

 error:
  Compatibility_CLEAR (module);

 do_return:
  Compatibility_ModuleReturn (module);
}


/*
 * Local variables:
 * coding: utf-8
 * mode: c
 * c-basic-offset: 2
 * indent-tabs-mode: nil
 * fill-column: 90
 * End:
 */
