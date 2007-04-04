/*--------------------------------------------------------------------*\
 * This file is part of Py-notify.                                    *
 *                                                                    *
 * Copyright (C) 2007 Paul Pogonyshev.                                *
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



/*- Type forward declarations --------------------------------------*/

typedef
struct
{
  PyObject_HEAD
  long int  num_active_protections;
}
FastGCProtector;


typedef
struct
{
  PyObject_HEAD
  PyObject *  protected_objects_dict;
  long int    num_active_protections;
}
DebugGCProtector;



/*- Functions forward declarations ---------------------------------*/

static void         AbstractGCProtector_dealloc     (PyObject *self);
static PyObject *   AbstractGCProtector_protect     (PyObject *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   AbstractGCProtector_unprotect   (PyObject *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   AbstractGCProtector_set_default (PyObject *null,
                                                     PyObject *arguments, PyObject *keywords);

static int          FastGCProtector_init            (FastGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static void         FastGCProtector_dealloc         (FastGCProtector *self);
static PyObject *   FastGCProtector_protect         (FastGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   FastGCProtector_unprotect       (FastGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   FastGCProtector_get_num_active_protections
                      (FastGCProtector *self);

static int          DebugGCProtector_init           (DebugGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static void         DebugGCProtector_dealloc        (DebugGCProtector *self);
static PyObject *   DebugGCProtector_protect        (DebugGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   DebugGCProtector_unprotect      (DebugGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   DebugGCProtector_get_num_object_protections
                                                    (DebugGCProtector *self,
                                                     PyObject *arguments, PyObject *keywords);
static PyObject *   DebugGCProtector_get_num_protected_objects
                      (DebugGCProtector *self);
static PyObject *   DebugGCProtector_get_num_active_protections
                      (DebugGCProtector *self);



/*- Documentation --------------------------------------------------*/

#define MODULE_DOC "\
A module for protecting objects from garbage collector.  Sometimes, objects that don't \
have a reference to them (and so are valid garbage collector targets) need to stay alive.  \
Good example of this are logic L{conditions <condition>}: their state can change because \
they have term conditions, yet they may be not referenced from anywhere, since handlers \
don't need a reference to notice a state change.\n\
\n\
This module defines both a simple L{interface <AbstractGCProtector>} and several \
implementations, some, which are suitable for production use (C{L{FastGCProtector}}), \
some for debugging purposes (C{L{DebugGCProtector}}.)\n\
\n\
Py-notify classes use value of the C{L{AbstractGCProtector.default}} variable as the \
protector instance.  In case you run into a problem, \
use C{L{AbstractGCProtector.set_default}} static method somewhere near your program beginning \
to set it to an instance of C{DebugGCProtector} or a similar class to track the problem down. \
However, we believe that Py-notify classes must not cause problems themselves, they may pop up \
only if you use a garbage-collection protector yourself."


#define ABSTRACT_GC_PROTECTOR_DOC                                       \
  NULL

#define ABSTRACT_GC_PROTECTOR_PROTECT_DOC "\
protect(self, object) \
\n\
Protect C{object} from being garbage-collected.  It is legal to protect same C{object} \
several times and an object is prevented from being garbage-collected if it has been \
protected at least once.  As a special case, if C{object} is C{None}, this function does \
nothing.\n\
\n\
For convenience, this function always returns C{object} itself.\n\
\n\
@rtype: object"

#define ABSTRACT_GC_PROTECTOR_UNPROTECT_DOC "\
unprotect(self, object) \
\n\
Unprotect C{object}.  If has been protected once only or exactly one time more than times it \
has been unprotected, make it a legal target for garbage collection again.  It is an error \
to call C{unprotect} more times than C{protect} for a same object, and descendant behaviour \
in this case is undefined.  It may even crash Python.  However, as a special case, if \
C{object} is C{None}, this function does nothing.  In particular, it is legal to `unprotect' \
C{None} without having protected it first, because it will be a no-op and not lead to bugs.\n\
\n\
\n\
For convenience, this function always returns C{object} itself.\n\
\n\
@rtype: object"

#define ABSTRACT_GC_PROTECTOR_SET_DEFAULT_DOC "\
set_default(protector) \
\n\
Set the value of the C{L{default}} variable.  You are advised to do this only once (if at all) \
somewhere near beginning of your program, because switching protectors being used may even \
crash Python.  A good reason for calling C{set_default} might be a need to debug protection \
problems, e.g. with a C{L{DebugGCProtector}}."


#define FAST_GC_PROTECTOR_DOC "\
Default fast implementation of C{AbstractGCProtector} interface.  It is suitable for \
production use, but difficult to debug problems with, because it doesn't track what has and \
what has not be protected.  For that purpose, use C{L{DebugGCProtector}}."

#define FAST_GC_PROTECTOR_PROTECT_DOC                                   \
  NULL

#define FAST_GC_PROTECTOR_UNPROTECT_DOC                                 \
  NULL

#define FAST_GC_PROTECTOR_NUM_ACTIVE_PROTECTIONS_DOC                    \
  NULL


#define DEBUG_GC_PROTECTOR_DOC "\
Implementation of C{AbstractGCProtector} interface suitable for debugging possible problems. \
Instances of this class track what they have protected so far and how many times.  If you \
try to unprotect an object more times than it has been protected, a stack trace will be \
printed and nothing will be done.  Note that no exception will be thrown.\n\
\n\
There is also a number of functions and properties in this class that allow you to retrieve \
various protection information."

#define DEBUG_GC_PROTECTOR_PROTECT_DOC                                  \
  NULL

#define DEBUG_GC_PROTECTOR_UNPROTECT_DOC                                \
  NULL

#define DEBUG_GC_PROTECTOR_GET_NUM_OBJECT_PROTECTIONS                   \
  NULL

#define DEBUG_GC_PROTECTOR_NUM_PROTECTED_OBJECTS_DOC                    \
  NULL

#define DEBUG_GC_PROTECTOR_NUM_ACTIVE_PROTECTIONS_DOC                   \
  NULL



/*- Types ----------------------------------------------------------*/

PyMethodDef  AbstractGCProtector_methods[]
  = { { "protect",     (PyCFunction)  AbstractGCProtector_protect,
        METH_VARARGS | METH_KEYWORDS,             ABSTRACT_GC_PROTECTOR_PROTECT_DOC },
      { "unprotect",   (PyCFunction)  AbstractGCProtector_unprotect,
        METH_VARARGS | METH_KEYWORDS,               ABSTRACT_GC_PROTECTOR_UNPROTECT_DOC },
      { "set_default", (PyCFunction)  AbstractGCProtector_set_default,
        METH_VARARGS | METH_KEYWORDS | METH_STATIC, ABSTRACT_GC_PROTECTOR_SET_DEFAULT_DOC },
      { NULL, NULL, 0, NULL } };

PyTypeObject  AbstractGCProtector_Type
  = { PyObject_HEAD_INIT (NULL)
      0,                                             /* ob_size           */
      "notify.gc.AbstractGCProtector",               /* tp_name           */
      sizeof (PyObject),                             /* tp_basicsize      */
      0,                                             /* tp_itemsize       */
      (destructor)     AbstractGCProtector_dealloc,  /* tp_dealloc        */
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
      Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,      /* tp_flags          */
      ABSTRACT_GC_PROTECTOR_DOC,                     /* tp_doc            */
      (traverseproc)   0,                            /* tp_traverse       */
      (inquiry)        0,                            /* tp_clear          */
      (richcmpfunc)    0,                            /* tp_richcompare    */
      0,                                             /* tp_weaklistoffset */
      (getiterfunc)    0,                            /* tp_iter           */
      (iternextfunc)   0,                            /* tp_iternext       */
      AbstractGCProtector_methods,                   /* tp_methods        */
      0,                                             /* tp_members        */
      0,                                             /* tp_getset         */
      (PyTypeObject *) &PyBaseObject_Type,           /* tp_base           */
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


PyMethodDef  FastGCProtector_methods[]
  = { { "protect",     (PyCFunction)  FastGCProtector_protect,
        METH_VARARGS | METH_KEYWORDS, FAST_GC_PROTECTOR_PROTECT_DOC },
      { "unprotect",   (PyCFunction)  FastGCProtector_unprotect,
        METH_VARARGS | METH_KEYWORDS, FAST_GC_PROTECTOR_UNPROTECT_DOC },
      { NULL, NULL, 0, NULL } };

PyGetSetDef  FastGCProtector_properties[]
  = { { "num_active_protections", (getter) FastGCProtector_get_num_active_protections, NULL,
        FAST_GC_PROTECTOR_NUM_ACTIVE_PROTECTIONS_DOC, NULL },
      { NULL, NULL, NULL, NULL, NULL } };

PyTypeObject  FastGCProtector_Type
  = { PyObject_HEAD_INIT (NULL)
      0,                                             /* ob_size           */
      "notify.gc.FastGCProtector",                   /* tp_name           */
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
      Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,      /* tp_flags          */
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
      (PyTypeObject *) &AbstractGCProtector_Type,    /* tp_base           */
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


PyMethodDef  DebugGCProtector_methods[]
  = { { "protect",     (PyCFunction)  DebugGCProtector_protect,
        METH_VARARGS | METH_KEYWORDS, DEBUG_GC_PROTECTOR_PROTECT_DOC },
      { "unprotect",   (PyCFunction)  DebugGCProtector_unprotect,
        METH_VARARGS | METH_KEYWORDS, DEBUG_GC_PROTECTOR_UNPROTECT_DOC },
      { "get_num_object_protections", (PyCFunction) DebugGCProtector_get_num_object_protections,
        METH_VARARGS | METH_KEYWORDS, DEBUG_GC_PROTECTOR_GET_NUM_OBJECT_PROTECTIONS },
      { NULL, NULL, 0, NULL } };

PyGetSetDef  DebugGCProtector_properties[]
  = { { "num_protected_objects", (getter) DebugGCProtector_get_num_protected_objects, NULL,
        DEBUG_GC_PROTECTOR_NUM_PROTECTED_OBJECTS_DOC, NULL },
      { "num_active_protections", (getter) DebugGCProtector_get_num_active_protections, NULL,
        DEBUG_GC_PROTECTOR_NUM_ACTIVE_PROTECTIONS_DOC, NULL },
      { NULL, NULL, NULL, NULL, NULL } };

PyTypeObject  DebugGCProtector_Type
  = { PyObject_HEAD_INIT (NULL)
      0,                                             /* ob_size           */
      "notify.gc.DebugGCProtector",                  /* tp_name           */
      sizeof (DebugGCProtector),                     /* tp_basicsize      */
      0,                                             /* tp_itemsize       */
      (destructor)     DebugGCProtector_dealloc,     /* tp_dealloc        */
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
      Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,      /* tp_flags          */
      DEBUG_GC_PROTECTOR_DOC,                        /* tp_doc            */
      (traverseproc)   0,                            /* tp_traverse       */
      (inquiry)        0,                            /* tp_clear          */
      (richcmpfunc)    0,                            /* tp_richcompare    */
      0,                                             /* tp_weaklistoffset */
      (getiterfunc)    0,                            /* tp_iter           */
      (iternextfunc)   0,                            /* tp_iternext       */
      DebugGCProtector_methods,                      /* tp_methods        */
      0,                                             /* tp_members        */
      DebugGCProtector_properties,                   /* tp_getset         */
      (PyTypeObject *) &AbstractGCProtector_Type,    /* tp_base           */
      (PyObject *)     0,                            /* tp_dict           */
      0,                                             /* tp_descr_get      */
      0,                                             /* tp_descr_set      */
      0,                                             /* tp_dictoffset     */
      (initproc)       DebugGCProtector_init,        /* tp_init           */
      (allocfunc)      0,                            /* tp_alloc          */
      (newfunc)        0,                            /* tp_new            */
      (freefunc)       0,                            /* tp_free           */
      (inquiry)        0,                            /* tp_is_gc          */
      (PyObject *)     0,                            /* tp_bases          */
    };



/*- Static variables -----------------------------------------------*/

static PyObject *  raise_not_implemented_exception;

static char *      no_keywords[]     = { NULL };
static char *      object_keywords[] = { "object", NULL };



/*- AbstractGCProtector type methods -------------------------------*/

static void
AbstractGCProtector_dealloc (PyObject *self)
{
  self->ob_type->tp_free (self);
}


static PyObject *
AbstractGCProtector_protect (PyObject *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify.gc.AbstractGCProtector.protect",
                                    object_keywords, &object))
    return NULL;

  return PyObject_CallFunction (raise_not_implemented_exception, "Os", self, "protect");
}


static PyObject *
AbstractGCProtector_unprotect (PyObject *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify.gc.AbstractGCProtector.unprotect",
                                    object_keywords, &object))
    return NULL;

  return PyObject_CallFunction (raise_not_implemented_exception, "Os", self, "unprotect");
}


static PyObject *
AbstractGCProtector_set_default (PyObject *null, PyObject *arguments, PyObject *keywords)
{
  static char *  protector_keywords[] = { "protector", NULL };

  PyObject *new_protector;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O!:notify.gc.AbstractGCProtector.unprotect",
                                    protector_keywords, &AbstractGCProtector_Type, &new_protector))
    return NULL;

  PyDict_SetItemString (AbstractGCProtector_Type.tp_dict, "default", new_protector);

  Py_INCREF (Py_None);
  return Py_None;
}



/*- FastGCProtector type methods -----------------------------------*/

static PyObject *
FastGCProtector_new (void)
{
  return PyObject_CallFunctionObjArgs ((PyObject *) &FastGCProtector_Type, NULL);
}


static int
FastGCProtector_init (FastGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  if (!PyArg_ParseTupleAndKeywords (arguments, keywords, ":notify.gc.FastGCProtector",
                                    no_keywords))
    return -1;

  return 0;
}


static void
FastGCProtector_dealloc (FastGCProtector *self)
{
  self->ob_type->tp_free ((PyObject *) self);
}


static PyObject *
FastGCProtector_protect (FastGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify.gc.FastGCProtector.protect",
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
                                    "O:notify.gc.FastGCProtector.protect",
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



/*- DebugGCProtector type methods ----------------------------------*/

static int
DebugGCProtector_init (DebugGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  if (!PyArg_ParseTupleAndKeywords (arguments, keywords, ":notify.gc.DebugGCProtector",
                                    no_keywords))
    return -1;

  Py_XDECREF (self->protected_objects_dict);
  self->protected_objects_dict = PyDict_New ();

  return 0;
}


static void
DebugGCProtector_dealloc (DebugGCProtector *self)
{
  Py_DECREF (self->protected_objects_dict);
  self->ob_type->tp_free ((PyObject *) self);
}


static PyObject *
DebugGCProtector_protect (DebugGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify.gc.DebugGCProtector.protect",
                                    object_keywords, &object))
    return NULL;

  if (object != Py_None)
    {
      PyObject *id;
      PyObject *num_protections;
      int       num_protections_new;

      id              = PyLong_FromVoidPtr (object);
      num_protections = PyDict_GetItem (self->protected_objects_dict, id);

      if (num_protections)
        num_protections_new = PyInt_AsLong (num_protections) + 1;
      else
        num_protections_new = 1;

      num_protections = PyInt_FromLong (num_protections_new);
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
DebugGCProtector_unprotect (DebugGCProtector *self, PyObject *arguments, PyObject *keywords)
{
  PyObject *object;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify.gc.DebugGCProtector.unprotect",
                                    object_keywords, &object))
    return NULL;

  if (object != Py_None)
    {
      PyObject *id;
      PyObject *num_protections;

      id              = PyLong_FromVoidPtr (object);
      num_protections = PyDict_GetItem (self->protected_objects_dict, id);

      if (num_protections)
        {
          int  num_protections_new = PyInt_AsLong (num_protections) - 1;

          if (num_protections_new)
            {
              num_protections = PyInt_FromLong (num_protections_new);
              PyDict_SetItem (self->protected_objects_dict, id, num_protections);
              Py_DECREF (num_protections);
            }
          else
            PyDict_DelItem (self->protected_objects_dict, id);

          --self->num_active_protections;
        }
      else
        {
          PyErr_SetString (PyExc_ValueError, "object is not protected by this DebugGCProtector");
          PyErr_Print ();

          /* So that the return statement at the end does no implicit unprotection. */
          Py_INCREF (object);
        }

      Py_DECREF (id);
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
DebugGCProtector_get_num_object_protections (DebugGCProtector *self,
                                             PyObject *arguments, PyObject *keywords)
{
  PyObject *object;
  PyObject *id;
  PyObject *num_protections;

  if (!PyArg_ParseTupleAndKeywords (arguments, keywords,
                                    "O:notify.gc.DebugGCProtector.unprotect",
                                    object_keywords, &object))
    return NULL;

  id              = PyLong_FromVoidPtr (object);
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
DebugGCProtector_get_num_protected_objects (DebugGCProtector *self)
{
  return PyInt_FromLong (PyDict_Size (self->protected_objects_dict));
}


static PyObject *
DebugGCProtector_get_num_active_protections (DebugGCProtector *self)
{
  return PyInt_FromLong (self->num_active_protections);
}



/*- Module initialization ------------------------------------------*/

#define REGISTER_TYPE(dictionary, type, name)                           \
  do                                                                    \
    {                                                                   \
      type.ob_type  = &PyType_Type;                                     \
      type.tp_alloc = PyType_GenericAlloc;                              \
      type.tp_new   = PyType_GenericNew;                                \
      if (PyType_Ready (&type) == 0)                                    \
        PyDict_SetItemString (dictionary, name, (PyObject *) &type);    \
    }                                                                   \
  while (0)


DL_EXPORT (void)
initgc (void)
{
  PyObject *module;
  PyObject *dictionary;
  PyObject *utilities;
  PyObject *default_protector;

  module     = Py_InitModule ("notify.gc", NULL);
  dictionary = PyModule_GetDict (module);

  utilities                       = PyImport_ImportModule ("notify.utils");
  raise_not_implemented_exception = PyDict_GetItemString (PyModule_GetDict (utilities),
                                                          "raise_not_implemented_exception");

  REGISTER_TYPE (dictionary, AbstractGCProtector_Type, "AbstractGCProtector");
  REGISTER_TYPE (dictionary, FastGCProtector_Type,     "FastGCProtector");
  REGISTER_TYPE (dictionary, DebugGCProtector_Type,    "DebugGCProtector");

  default_protector = FastGCProtector_new ();
  PyDict_SetItemString (AbstractGCProtector_Type.tp_dict, "default", default_protector);
  Py_DECREF (default_protector);

  PyModule_AddStringConstant (module, "__doc__", MODULE_DOC);
  PyModule_AddStringConstant (module, "__docformat__", "epytext en");
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
